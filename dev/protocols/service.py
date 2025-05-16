from abc import abstractmethod


class Service:
    @abstractmethod
    async def handle_request(self, request, ctx=None):
        pass
