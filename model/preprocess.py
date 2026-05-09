import re

import jieba


def clean_text(text):
    if not isinstance(text, str):
        return ''
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#([^#]+)#', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def cut_words(text):
    return list(jieba.cut(text))


def segment_text(text):
    return ' '.join(cut_words(clean_text(text)))


def pad_sequence(seq, max_len):
    if len(seq) > max_len:
        return seq[:max_len]
    return seq + [0] * (max_len - len(seq))


def text_to_sequence(words, vocab):
    return [vocab.get(word, 1) for word in words]
