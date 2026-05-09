# Sentiment Model Service

这是博客评论情感分析的独立推理服务。博客后端通过 `SENTIMENT_SERVICE_URL` 调用它。

## API

```http
POST /api/predict
Content-Type: application/json

{"text": "这篇文章写得很好"}
```

响应：

```json
{
  "ok": true,
  "label": "positive",
  "sentiment": "正面",
  "score": 0.93,
  "confidence": 0.93,
  "probabilities": {
    "positive": 0.93,
    "neutral": 0.0,
    "negative": 0.07
  },
  "probabilitiesZh": {
    "正面": 0.93,
    "中性": 0.0,
    "负面": 0.07
  },
  "engine": "bilstm"
}
```

## 模型文件

把训练好的模型产物放到 `model/artifacts/`。

默认 `MODEL_TYPE=bilstm`，需要这些文件：

```text
model/artifacts/bilstm_model.pth
model/artifacts/bilstm_config.pkl
model/artifacts/vocab_bilstm.pkl
```

也支持：

```text
MODEL_TYPE=textcnn
model/artifacts/textcnn_model.pth
model/artifacts/model_config.pkl
model/artifacts/vocab.pkl
```

```text
MODEL_TYPE=svm
model/artifacts/svm_model.pkl
model/artifacts/tfidf.pkl
```

```text
MODEL_TYPE=bert
model/artifacts/bert_model/
```

BERT 需要在 `requirements.txt` 中启用 `transformers` 依赖。
