import inspect
from functools import wraps

from flask import current_app, request
from flask.ext import restful
from flask.ext.restful.utils import unpack


def crossdomain(func=None, *args, **kwargs):
    """A decorator that adds CORS support to resources and methods

    :param allow_credentials: Set the header `Access-Control-Allow-Credentials`
        If not provided, it defaults to `False`
    :type allow_credentials: bool
    :param allow_headers: Set the header `Access-Control-Allow-Headers`
        If not provided, it defaults to "accept, content-type"
    :type resource: str
    :param allow_origin: Set the header `Access-Control-Allow-Origin`
        If not provided, it defaults to "*"
    :type resource: str
    :param expose_headers: Set the header `Access-Control-Expose-Headers`
        If not provided the header is not sent
    :type resource: str
    :param max_age: Set the header `Access-Control-Max-Age`
        If not provided, it defaults to 21600 seconds
    :type resource: int

    Examples::

        class DummyResource(Resource):

            @crossdomain
            def get(self):
                return []

            @crossdomain(max_age=180)
            def post(self):
                return []

        @crossdomain(allow_headers="accept, content-type")
        class CORSResource(Resource):

            def get(self):
                return []

            @crossdomain(max_age=180)  # overwrite resource value for max_age
            def post(self):
                return []
    """
    if func:
        if not args and not kwargs:
            return CORS()(func)
        else:
            return CORS(*args, **kwargs)(func)
    else:
        if not args and not kwargs:
            return CORS()
        else:
            return CORS(*args, **kwargs)


class CORS(object):

    def __init__(self, allow_credentials=None, allow_headers=None,
                 allow_origin=None, expose_headers=None, max_age=None):
        self.allow_credentials = allow_credentials or False
        self.allow_headers = allow_headers or "accept, content-type"
        self.allow_origin = allow_origin or "*"
        self.expose_headers = expose_headers
        self.max_age = max_age or 21600

    def __call__(self, obj):
        decorator = CORS(
            allow_credentials=self.allow_credentials,
            allow_headers=self.allow_headers,
            allow_origin=self.allow_origin,
            expose_headers=self.expose_headers,
            max_age=self.max_age
        )
        try:
            obj.cors_decorator = decorator
        except AttributeError:
            pass  # avoid adding the self-aware decorator signal to everything
        if inspect.isclass(obj) and issubclass(obj, restful.Resource):
            # Decorate the whole resource
            cls = obj
            cls_dict = dict(cls.__dict__)
            cls_dict["provide_automatic_options"] = False
            for method_name in cls_dict['methods']:
                method_lower = method_name.lower()
                method = cls_dict[method_lower]
                cls_dict[method_lower] = decorator(method)
            if "OPTIONS" not in cls.methods:
                cls_dict['methods'] += ["OPTIONS"]
            CORSClass = type(cls.__class__.__name__, cls.__bases__, cls_dict)
            return CORSClass
        else:
            # Decorate just a method
            func = obj

            @wraps(func)
            def wrapper(*args, **kwargs):
                """Implement the W3C specification at
                http://www.w3.org/TR/cors/#resource-processing-model"""
                resp = func(*args, **kwargs)
                if "Origin" not in request.headers:
                    return resp
                else:
                    data, code, headers = unpack(resp)
                    cors_headers = self.get_headers(func)
                    cors_headers.update(headers)
                    return data, code, cors_headers
            return wrapper

    def get_headers(self, func):
        methods = current_app.make_default_options_response().headers["Allow"]
        current_method = func.__name__.upper()
        if current_method not in methods:
            methods += current_method
        allow_origin = request.headers.get("Origin", self.allow_origin)
        cors_headers = {
            "Access-Control-Allow-Headers": self.allow_headers,
            "Access-Control-Allow-Origin": allow_origin,
            "Access-Control-Allow-Methods": methods,
            "Access-Control-Max-Age": str(self.max_age),
        }
        if self.expose_headers:
            cors_headers.update({
                "Access-Control-Expose-Headers": self.expose_headers,
            })
        if self.allow_credentials and request.cookies:
            cors_headers.update({
                "Access-Control-Allow-Credentials": "true",
            })
        return cors_headers
