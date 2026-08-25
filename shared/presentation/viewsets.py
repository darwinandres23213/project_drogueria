from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT


class SoftDestroyModelMixin:
    """Eliminación lógica cuando el modelo soporta deleted_at."""

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()


class SoftModelViewSet(
    SoftDestroyModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """ModelViewSet con soft delete."""

    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']
