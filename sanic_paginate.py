import json

from bson import json_util


class Pagination:
    """A simple pagination for web frameworks."""
    _page_name = 'page'
    _per_page_name = 'per_page'
    _max_per_page = 100  # prevent malicious user to load too many records
    data = None
    total = None

    def __init__(self, request=None, data=None, total=None, **kwargs):
        if request is None and 'url' not in kwargs and data is None:
            raise ValueError('request or url or data is required')

        kwargs.setdefault('page_name', self._page_name)
        kwargs.setdefault('per_page_name', self._per_page_name)
        if request is not None:
            if 'url' not in kwargs:
                if hasattr(request, 'path'):
                    url = request.url
                else:
                    if request.query_string:
                        url = '{}?{}'.format(request.url, request.query_string)
                    else:
                        url = request.url

                kwargs.update(url=url)

            page_name = kwargs['page_name']
            per_page_name = kwargs['per_page_name']
            page, per_page, skip = self.get_page_args(request, page_name,
                                                      per_page_name)
            self.page = page
            self.per_page = per_page
            self.skip = skip

            kwargs.setdefault(page_name, page)
            kwargs.setdefault(per_page_name, per_page)

            self.data = data
            self.total = total

    def toJSON(self):
        return json.dumps({"data": self.data, "page": self.page, "per_page": self.per_page, "total": self.total,
                           "offset": self.skip}, ensure_ascii=False, default=json_util.default)

    @staticmethod
    def get_page_args(request, page_name=None, per_page_name=None):
        page = request.args.get(page_name or Pagination._page_name, 1)
        per_page = request.args.get(per_page_name or Pagination._per_page_name,
                                    10)
        try:
            per_page = int(per_page)
        except:
            per_page = 10

        try:
            page = int(page)
        except:
            page = 1

        return page, per_page, per_page * (page - 1)
