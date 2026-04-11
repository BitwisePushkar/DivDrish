from flask import jsonify, request

def success_response(data, status_code=200, message="Success"):
    response = {
        "status": "success",
        "message": message,
        "data": data,
    }
    request_id = getattr(request, "request_id", None) if request else None
    if request_id:
        response["request_id"] = request_id
    return jsonify(response), status_code

def error_response(message, status_code=400, details=None):
    response = {
        "status": "error",
        "error": message,
        "status_code": status_code,
    }
    if details is not None:
        response["detail"] = details
    try:
        request_id = getattr(request, "request_id", None)
        if request_id:
            response["request_id"] = request_id
    except RuntimeError:
        pass
    return jsonify(response), status_code

def paginated_response(items, total, page, page_size):
    return success_response({
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": items,
    })