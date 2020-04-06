import torch
import torch.nn as nn
import math


class Dense(nn.Module):
    def __init__(self, *Ws):
        super(Dense, self).__init__()
        self.Ws = nn.ModuleList(list(Ws))
        if len(Ws) > 0 and hasattr(Ws[0], 'out_features'):
            self.out_features = Ws[0].out_features

    def forward(self, *xs):
        xs = xs[-len(self.Ws):]
        out = sum(W(x) for x, W in zip(xs, self.Ws) if W is not None)
        return out


class DenseSequential(nn.Sequential):
    def forward(self, x):
        xs = [x]
        for module in self._modules.values():
            if 'Dense' in type(module).__name__:
                xs.append(module(*xs))
            else:
                xs.append(module(xs[-1]))
        return xs[-1]


class Flatten(nn.Module):
    def forward(self, x):
        return x.view(x.size(0), -1)


def model_resnet(in_ch, in_dim, width=1, N=1):
    def block(in_filters, out_filters, k, downsample):
        if not downsample:
            k_first = 3
            skip_stride = 1
            k_skip = 1
        else:
            k_first = 4
            skip_stride = 2
            k_skip = 2
        return [
            Dense(nn.Conv2d(in_filters, out_filters, k_first, stride=skip_stride, padding=1)),
            nn.ReLU(),
            Dense(nn.Conv2d(in_filters, out_filters, k_skip, stride=skip_stride, padding=0),
                  None,
                  nn.Conv2d(out_filters, out_filters, k, stride=1, padding=1)),
            nn.ReLU()
        ]

    conv1 = [nn.Conv2d(in_ch, 16, 3, stride=1, padding=3 if in_dim == 28 else 1), nn.ReLU()]
    conv2 = block(16, 16 * width, 3, False)
    for _ in range(N):
        conv2.extend(block(16 * width, 16 * width, 3, False))
    conv3 = block(16 * width, 32 * width, 3, True)
    for _ in range(N - 1):
        conv3.extend(block(32 * width, 32 * width, 3, False))
    conv4 = block(32 * width, 64 * width, 3, True)
    for _ in range(N - 1):
        conv4.extend(block(64 * width, 64 * width, 3, False))
    layers = (
            conv1 +
            conv2 +
            conv3 +
            conv4 +
            [Flatten(),
             nn.Linear(64 * width * 8 * 8, 1000),
             nn.ReLU(),
             nn.Linear(1000, 10)]
    )
    model = DenseSequential(
        *layers
    )

    for m in model.modules():
        if isinstance(m, nn.Conv2d):
            n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
            m.weight.data.normal_(0, math.sqrt(2. / n))
            if m.bias is not None:
                m.bias.data.zero_()
    return model


if __name__ == "__main__":
    model = model_resnet(in_ch=1, in_dim=28)
    dummy = torch.randn(8, 1, 28, 28)
    print(model(dummy).shape)
