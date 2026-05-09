import os
import pickle
from pathlib import Path

import joblib
import numpy as np
import torch

from model_defs import BiLSTM, TextCNN
from preprocess import clean_text, cut_words, pad_sequence, segment_text, text_to_sequence


class ModelNotReady(RuntimeError):
    pass


def normalize_result(sentiment, prob_neg, prob_pos, cleaned, engine):
    probabilities = {
        'positive': float(prob_pos),
        'neutral': 0.0,
        'negative': float(prob_neg),
    }
    label = 'positive' if prob_pos >= prob_neg else 'negative'
    score = probabilities[label]
    return {
        'label': label,
        'sentiment': '正面' if label == 'positive' else '负面',
        'score': score,
        'confidence': score,
        'probabilities': probabilities,
        'probabilitiesZh': {
            '正面': float(prob_pos),
            '中性': 0.0,
            '负面': float(prob_neg),
        },
        'cleaned': cleaned,
        'engine': engine,
        'legacySentiment': sentiment,
    }


class BasePredictor:
    name = 'base'

    def predict(self, text):
        raise NotImplementedError


class BiLSTMPredictor(BasePredictor):
    name = 'bilstm'

    def __init__(self, artifacts_dir):
        self.device = torch.device(os.getenv('TORCH_DEVICE', 'cpu'))
        config_path = artifacts_dir / 'bilstm_config.pkl'
        vocab_path = artifacts_dir / 'vocab_bilstm.pkl'
        model_path = artifacts_dir / 'bilstm_model.pth'
        for path in [config_path, vocab_path, model_path]:
            if not path.exists():
                raise ModelNotReady('缺少 BiLSTM 模型文件: {}'.format(path))

        with config_path.open('rb') as file:
            self.config = pickle.load(file)
        with vocab_path.open('rb') as file:
            self.vocab = pickle.load(file)

        self.model = BiLSTM(
            vocab_size=self.config['vocab_size'],
            embedding_dim=self.config['embedding_dim'],
            hidden_dim=self.config['hidden_dim'],
            num_layers=self.config['num_layers'],
            num_classes=self.config['num_classes'],
            dropout_rate=self.config.get('dropout_rate', 0.5),
        ).to(self.device)
        state = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(state)
        self.model.eval()
        self.max_len = self.config['max_len']

    def predict(self, text):
        cleaned = clean_text(text)
        words = cut_words(cleaned)
        seq = text_to_sequence(words, self.vocab)
        padded = pad_sequence(seq, self.max_len)
        input_tensor = torch.LongTensor([padded]).to(self.device)

        with torch.no_grad():
            output = self.model(input_tensor)
            probs = torch.softmax(output, dim=1).cpu().numpy()[0]

        prob_neg = float(probs[0])
        prob_pos = float(probs[1])
        sentiment = '正面' if prob_pos > prob_neg else '负面'
        return normalize_result(sentiment, prob_neg, prob_pos, cleaned, self.name)


class TextCNNPredictor(BasePredictor):
    name = 'textcnn'

    def __init__(self, artifacts_dir):
        self.device = torch.device(os.getenv('TORCH_DEVICE', 'cpu'))
        config_path = artifacts_dir / 'model_config.pkl'
        vocab_path = artifacts_dir / 'vocab.pkl'
        model_path = artifacts_dir / 'textcnn_model.pth'
        for path in [config_path, vocab_path, model_path]:
            if not path.exists():
                raise ModelNotReady('缺少 TextCNN 模型文件: {}'.format(path))

        with config_path.open('rb') as file:
            self.config = pickle.load(file)
        with vocab_path.open('rb') as file:
            self.vocab = pickle.load(file)

        self.model = TextCNN(
            vocab_size=self.config['vocab_size'],
            embedding_dim=self.config['embedding_dim'],
            num_filters=self.config['num_filters'],
            filter_sizes=self.config['filter_sizes'],
            num_classes=self.config['num_classes'],
            dropout_rate=self.config.get('dropout_rate', 0.5),
        ).to(self.device)
        state = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(state)
        self.model.eval()
        self.max_len = self.config['max_len']

    def predict(self, text):
        cleaned = clean_text(text)
        words = cut_words(cleaned)
        seq = text_to_sequence(words, self.vocab)
        padded = pad_sequence(seq, self.max_len)
        input_tensor = torch.LongTensor([padded]).to(self.device)

        with torch.no_grad():
            output = self.model(input_tensor)
            probs = torch.softmax(output, dim=1).cpu().numpy()[0]

        prob_neg = float(probs[0])
        prob_pos = float(probs[1])
        sentiment = '正面' if prob_pos > prob_neg else '负面'
        return normalize_result(sentiment, prob_neg, prob_pos, cleaned, self.name)


class SVMPredictor(BasePredictor):
    name = 'svm'

    def __init__(self, artifacts_dir):
        model_path = artifacts_dir / 'svm_model.pkl'
        vectorizer_path = artifacts_dir / 'tfidf.pkl'
        for path in [model_path, vectorizer_path]:
            if not path.exists():
                raise ModelNotReady('缺少 SVM 模型文件: {}'.format(path))
        self.model = joblib.load(model_path)
        self.vectorizer = joblib.load(vectorizer_path)

    def predict(self, text):
        cleaned = clean_text(text)
        segmented = segment_text(cleaned)
        features = self.vectorizer.transform([segmented])
        pred = self.model.predict(features)[0]
        probs = self.model.predict_proba(features)[0]
        prob_neg = float(probs[0])
        prob_pos = float(probs[1])
        sentiment = '正面' if int(pred) == 1 else '负面'
        return normalize_result(sentiment, prob_neg, prob_pos, cleaned, self.name)


class BertPredictor(BasePredictor):
    name = 'bert'

    def __init__(self, artifacts_dir):
        try:
            from transformers import BertForSequenceClassification, BertTokenizer
        except ImportError as exc:
            raise ModelNotReady('BERT 推理需要安装 transformers: {}'.format(exc)) from exc

        model_dir = artifacts_dir / 'bert_model'
        if not model_dir.exists():
            raise ModelNotReady('缺少 BERT 模型目录: {}'.format(model_dir))
        self.device = torch.device(os.getenv('TORCH_DEVICE', 'cpu'))
        self.max_len = int(os.getenv('BERT_MAX_LENGTH', '128'))
        self.tokenizer = BertTokenizer.from_pretrained(str(model_dir))
        self.model = BertForSequenceClassification.from_pretrained(str(model_dir)).to(self.device)
        self.model.eval()

    def predict(self, text):
        cleaned = clean_text(text)
        encoding = self.tokenizer(
            cleaned,
            add_special_tokens=True,
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_tensors='pt',
        )
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)

        with torch.no_grad():
            output = self.model(input_ids, attention_mask=attention_mask)
            probs = torch.softmax(output.logits, dim=1).cpu().numpy()[0]

        prob_neg = float(probs[0])
        prob_pos = float(probs[1])
        sentiment = '正面' if np.argmax(probs) == 1 else '负面'
        return normalize_result(sentiment, prob_neg, prob_pos, cleaned, self.name)


def create_predictor():
    artifacts_dir = Path(os.getenv('MODEL_ARTIFACTS_DIR', '/app/artifacts'))
    model_type = os.getenv('MODEL_TYPE', 'bilstm').strip().lower()
    registry = {
        'bilstm': BiLSTMPredictor,
        'textcnn': TextCNNPredictor,
        'svm': SVMPredictor,
        'bert': BertPredictor,
    }
    if model_type not in registry:
        raise ModelNotReady('不支持的 MODEL_TYPE: {}'.format(model_type))
    return registry[model_type](artifacts_dir)
