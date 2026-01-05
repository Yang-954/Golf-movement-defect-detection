import torch
import torch.nn as nn
from MobileNetV2 import MobileNetV2
from pathlib import Path


class EventDetector(nn.Module):
    def __init__(
        self,
        pretrain,
        width_mult,
        lstm_layers,
        lstm_hidden,
        bidirectional=True,
        dropout=True,
        num_events: int = 8,
    ):
        super(EventDetector, self).__init__()
        self.width_mult = width_mult
        self.lstm_layers = lstm_layers
        self.lstm_hidden = lstm_hidden
        self.bidirectional = bidirectional
        self.dropout = dropout
        self.num_events = num_events
        self.num_classes = num_events + 1  # last class is no-event/background

        net = MobileNetV2(width_mult=width_mult)
        mobilenet_weights = Path(__file__).resolve().parent / 'mobilenet_v2.pth.tar'
        try:
            state_dict_mobilenet = torch.load(str(mobilenet_weights), map_location='cpu', weights_only=True)
        except TypeError:
            state_dict_mobilenet = torch.load(str(mobilenet_weights), map_location='cpu')
        if pretrain:
            net.load_state_dict(state_dict_mobilenet)

        self.cnn = nn.Sequential(*list(net.children())[0][:19])
        self.rnn = nn.LSTM(int(1280*width_mult if width_mult > 1.0 else 1280),
                           self.lstm_hidden, self.lstm_layers,
                           batch_first=True, bidirectional=bidirectional)
        if self.bidirectional:
            self.lin = nn.Linear(2*self.lstm_hidden, self.num_classes)
        else:
            self.lin = nn.Linear(self.lstm_hidden, self.num_classes)
        if self.dropout:
            self.drop = nn.Dropout(0.5)

    def init_hidden(self, batch_size, device):
        if self.bidirectional:
            return (
                torch.zeros(2 * self.lstm_layers, batch_size, self.lstm_hidden, device=device),
                torch.zeros(2 * self.lstm_layers, batch_size, self.lstm_hidden, device=device),
            )
        else:
            return (
                torch.zeros(self.lstm_layers, batch_size, self.lstm_hidden, device=device),
                torch.zeros(self.lstm_layers, batch_size, self.lstm_hidden, device=device),
            )

    def forward(self, x, lengths=None):
        batch_size, timesteps, C, H, W = x.size()
        self.hidden = self.init_hidden(batch_size, x.device)

        # CNN forward
        c_in = x.view(batch_size * timesteps, C, H, W)
        c_out = self.cnn(c_in)
        c_out = c_out.mean(3).mean(2)
        if self.dropout:
            c_out = self.drop(c_out)

        # LSTM forward
        r_in = c_out.view(batch_size, timesteps, -1)
        r_out, states = self.rnn(r_in, self.hidden)
        out = self.lin(r_out)
        out = out.view(batch_size * timesteps, self.num_classes)

        return out



