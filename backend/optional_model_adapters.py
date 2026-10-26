"""Hooks only: configure after verifying a specific model checkpoint and its labels."""
def run_univfd(image, predictor=None):
    if predictor is None:
        return {"status": "unavailable", "message": "UnivFD predictor/checkpoint not configured."}
    return {"status": "completed", "result": predictor(image)}


def run_xceptionnet(face_image, predictor=None):
    if predictor is None:
        return {"status": "unavailable", "message": "XceptionNet predictor/checkpoint not configured."}
    return {"status": "completed", "result": predictor(face_image)}
