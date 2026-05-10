import os

from flask import Flask, jsonify, request

from inference import ModelNotReady, create_predictor


app = Flask(__name__)
predictor = None
startup_error = None


def load_model():
    global predictor, startup_error
    try:
        predictor = create_predictor()
        startup_error = None
    except Exception as exc:
        predictor = None
        startup_error = str(exc)


load_model()


@app.route('/health')
def health():
    return jsonify({
        'ok': predictor is not None,
        'modelLoaded': predictor is not None,
        'configuredModel': os.getenv('MODEL_TYPE', 'bilstm'),
        'engine': predictor.name if predictor else None,
        'device': os.getenv('TORCH_DEVICE', 'cpu'),
        'error': startup_error,
    }), 200 if predictor else 503


@app.route('/api/predict', methods=['POST'])
def predict():
    if predictor is None:
        return jsonify({'ok': False, 'message': startup_error or '模型未加载'}), 503

    payload = request.get_json(silent=True) or {}
    text = (payload.get('text') or '').strip()
    if not text:
        return jsonify({'ok': False, 'message': 'text 不能为空'}), 400

    try:
        result = predictor.predict(text)
    except ModelNotReady as exc:
        return jsonify({'ok': False, 'message': str(exc)}), 503
    except Exception as exc:
        return jsonify({'ok': False, 'message': '推理失败: {}'.format(exc)}), 500

    return jsonify({
        'ok': True,
        'text': text,
        **result,
    })


@app.route('/reload', methods=['POST'])
def reload_model():
    load_model()
    return jsonify({
        'ok': predictor is not None,
        'modelLoaded': predictor is not None,
        'configuredModel': os.getenv('MODEL_TYPE', 'bilstm'),
        'engine': predictor.name if predictor else None,
        'device': os.getenv('TORCH_DEVICE', 'cpu'),
        'error': startup_error,
    }), 200 if predictor else 503


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000)
