import torch
import torch.nn as nn


class BiLSTM(nn.Module):
    def __init__(self, vocab_size, embedding_dim, hidden_dim, num_layers, num_classes, dropout_rate=0.5):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout_rate if num_layers > 1 else 0,
        )
        self.dropout = nn.Dropout(dropout_rate)
        self.fc = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, x):
        x = self.embedding(x)
        _, (hidden, _) = self.lstm(x)
        forward_hidden = hidden[-2, :, :]
        backward_hidden = hidden[-1, :, :]
        x = torch.cat([forward_hidden, backward_hidden], dim=1)
        x = self.dropout(x)
        return self.fc(x)


class TextCNN(nn.Module):
    def __init__(self, vocab_size, embedding_dim, num_filters, filter_sizes, num_classes, dropout_rate=0.5):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.convs = nn.ModuleList([
            nn.Conv2d(
                in_channels=1,
                out_channels=num_filters,
                kernel_size=(filter_size, embedding_dim),
            )
            for filter_size in filter_sizes
        ])
        self.dropout = nn.Dropout(dropout_rate)
        self.fc = nn.Linear(len(filter_sizes) * num_filters, num_classes)

    def forward(self, x):
        x = self.embedding(x)
        x = x.unsqueeze(1)
        conv_outputs = []
        for conv in self.convs:
            conv_out = conv(x)
            conv_out = torch.relu(conv_out.squeeze(3))
            pooled = torch.max(conv_out, dim=2)[0]
            conv_outputs.append(pooled)
        x = torch.cat(conv_outputs, dim=1)
        x = self.dropout(x)
        return self.fc(x)
