from torch import nn
import math


class ChannelAttention(nn.Module):
    def __init__(self, num_features, reduction):
        super(ChannelAttention, self).__init__()
        self.module = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(num_features, num_features // reduction, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(num_features // reduction, num_features, kernel_size=1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return x * self.module(x)


class RCAB(nn.Module):
    def __init__(self, num_features, reduction):
        super(RCAB, self).__init__()
        self.module = nn.Sequential(
            nn.Conv2d(num_features, num_features, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(num_features, num_features, kernel_size=3, padding=1),
            ChannelAttention(num_features, reduction)
        )

    def forward(self, x):
        return x + self.module(x)


class RG(nn.Module):
    def __init__(self, num_features, num_rcab, reduction):
        super(RG, self).__init__()
        self.module = [RCAB(num_features, reduction) for _ in range(num_rcab)]
        self.module.append(nn.Conv2d(num_features, num_features, kernel_size=3, padding=1))
        self.module = nn.Sequential(*self.module)

    def forward(self, x):
        return x + self.module(x)

class RCAN(nn.Module):
    def __init__(self, scale = 8, num_features = 64, num_rg = 10, num_rcab = 20, reduction = 16):
        super(RCAN, self).__init__()
        scale = scale
        num_features = num_features
        num_rg = num_rg
        num_rcab = num_rcab
        reduction = reduction

        self.sf = nn.Conv2d(3, num_features, kernel_size=3, padding=1)
        self.rgs = nn.Sequential(*[RG(num_features, num_rcab, reduction) for _ in range(num_rg)])
        self.conv1 = nn.Conv2d(num_features, num_features, kernel_size=3, padding=1)

        self.upscale = []
        if (scale & (scale - 1)) == 0:    # Is scale = 2^n?
            for _ in range(int(math.log(scale, 2))):
                self.upscale.append(nn.Conv2d(num_features, 4 * num_features, kernel_size=3, padding=1))
                self.upscale.append(nn.PixelShuffle(2))
        else :
            print("scale is not 2^n !!")
        self.upscale = nn.Sequential(*self.upscale)

        # self.upscale = nn.Sequential(
        #     nn.Conv2d(num_features, num_features * (scale ** 2), kernel_size=3, padding=1),
        #     nn.PixelShuffle(scale)
        # )
        self.conv2 = nn.Conv2d(num_features, 3, kernel_size=3, padding=1)

    def forward(self, x):
        x = self.sf(x)
        residual = x
        x = self.rgs(x)
        x = self.conv1(x)
        x += residual
        x = self.upscale(x)
        x = self.conv2(x)
        return x
