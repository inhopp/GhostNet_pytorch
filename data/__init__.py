from .dataset import Dataset
import torch
import torchvision.transforms as transforms

def generate_loader(phase, opt):
    dataset = Dataset
    img_size = opt.img_size

    mean = (0.5, 0.5, 0.5)
    std = (0.5, 0.5, 0.5)

    if phase == 'train':
        transform =  transforms.Compose([
            transforms.Resize(img_size),
            transforms.Pad(6, padding_mode='reflect'), # img_size: (256,256)
            transforms.RandomCrop(img_size),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ])

    else:
        transform = transforms.Compose([
            transforms.Resize(img_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ])

    dataset = dataset(opt, phase, transform=transform)

    kwargs = {
        "batch_size": opt.batch_size if phase == 'train' else opt.eval_batch_szie,
        "shuffle": phase == 'train',
        "drop_last": phase == 'train',
    }

    return torch.utils.data.DataLoader(dataset, **kwargs)