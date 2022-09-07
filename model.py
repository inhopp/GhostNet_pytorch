from turtle import forward
import torch
import torch.nn as nn
import math

class SEUnit(nn.Module):
    '''Squeeze-Excitation Unit'''
    def __init__(self, in_channel, reduction_ratio=4, act=nn.ReLU):
        super(SEUnit, self).__init__()
        hidden_dim = in_channel // reduction_ratio
        self.fc1 = nn.Conv2d(in_channel, hidden_dim, (1,1), bias=True)
        self.fc2 = nn.Conv2d(hidden_dim, in_channel, (1,1), bias=True)
        self.act = act()

    def forward(self, x):
        out = x.mean((2,3), keepdim=True)
        out = self.fc1(out)
        out = self.act(out)
        out = self.fc2(out)
        out = self.act(out)
        return x * out


class GhostModule(nn.Module):
    def __init__(self, in_channel, out_channel, kernel_size=1, ratio=2, dw_kernel_size=3, stride=1, relu=True):
        super(GhostModule, self).__init__()
        self.out_channel = out_channel
        inter_channel = math.ceil(out_channel/ratio)
        new_channel = inter_channel * (ratio-1)

        self.primary_conv = nn.Sequential(
            nn.Conv2d(in_channel, inter_channel, kernel_size, stride, (kernel_size-1)//2, bias=False),
            nn.BatchNorm2d(inter_channel),
            nn.ReLU(inplace=True) if relu else nn.Sequential(),
        )

        self.cheap_operation = nn.Sequential(
            nn.Conv2d(inter_channel, new_channel, dw_kernel_size, 1, (dw_kernel_size-1)//2, groups=inter_channel, bias=False),
            nn.BatchNorm2d(new_channel),
            nn.ReLU(inplace=True) if relu else nn.Sequential(),
        )

    def forward(self, x):
        x1 = self.primary_conv(x)
        x2 = self.cheap_operation(x1)
        out = torch.cat([x1,x2], dim=1)
        
        return out[:,:self.out_channel,:,:]


class GBBolockConfig:
    def __init__(self, dw_kernel_size: int, inter_channel: int, out_channel: int, use_se: int, stride: int, in_channel: int):
        self.dw_kernel_size = dw_kernel_size
        self.inter_channel = inter_channel
        self.out_channel = out_channel
        self.use_se = True if use_se == 1 else False
        self.stride = stride
        self.in_channel = out_channel
        
        


class GhostBottleneck(nn.Module):
    def __init__(self, c): # c: block_config
        super(GhostBottleneck, self).__init__()
        self.stride = c.stride
        
        # channel expansion (pointwise conv)
        self.ghost1 = GhostModule(c.in_channel, c.inter_channel, relu=True)

        # depthwise conv
        if self.stride > 1:
            self.conv_dw = nn.Conv2d(c.inter_channel, c.inter_channel, c.dw_kernel_size, stride=c.stride, padding=(c.dw_kernel_size-1)//2, groups=c.inter_channel, bias=False)
            self.bn_dw = nn.BatchNorm2d(c.inter_channel)
        
        # squeeze-excitation
        if c.use_se:
            self.se = SEUnit(c.inter_channel)
        else:
            self.se = None

        # channel reduction (pointwise conv)
        self.ghost2 = GhostModule(c.inter_channel, c.out_channel, relu=False)

        # shortcut-connection
        self.shortcut_connection = c.stride==1 and c.in_channel==c.out_channel

    def forward(self, x):
        out = self.ghost1(x)

        if self.stride > 1:
            out = self.conv_dw(out)
            out = self.bn_dw(out)
        
        if self.se is not None:
            out = self.se(out)

        out = self.ghost2(out)

        if self.shortcut_connection:
            out += x

        return out



class GhostNet(nn.Module):
    def __init__(self, model_config, out_channels=1280, num_classes=1000, block=GhostBottleneck, act_layer=nn.ReLU, norm_layer=nn.BatchNorm2d):
        super(GhostNet, self).__init__()
        self.model_config = model_config
        self.norm_layer = norm_layer
        self.act_layer = act_layer

        


    def make_layers(self, model_config, block):
        layers = []

        for i in range(len(model_config)):
            layers.append(block(model_config[i]))

            if i < len(model_config) - 1:
                model_config[i+1].in_channel = model_config[i].out_channel
        
        return layers



def get_ghostnet_structure():
    return [
    ''' kernel_size, expasion_size, out_channels, use_se, stide '''
        [3,  16,  16, 0, 1],
        [3,  48,  24, 0, 2],
        [3,  72,  24, 0, 1],
        [5,  72,  40, 1, 2],
        [5, 120,  40, 1, 1],
        [3, 240,  80, 0, 2],
        [3, 200,  80, 0, 1],
        [3, 184,  80, 0, 1],
        [3, 184,  80, 0, 1],
        [3, 480, 112, 1, 1],
        [3, 672, 112, 1, 1],
        [5, 672, 160, 1, 2],
        [5, 960, 160, 0, 1],
        [5, 960, 160, 1, 1],
        [5, 960, 160, 0, 1],
        [5, 960, 160, 1, 1]
    ]