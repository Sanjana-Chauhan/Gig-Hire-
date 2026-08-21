"""API endpoints for the hiring workflow."""

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.gigs.models import Gig
from apps.hiring import services
from apps.hiring.models import Application
from apps.hiring.serializers import ApplicationSerializer, ApplyToGigSerializer


class ApplyToGigView(APIView):
    """``POST /api/gigs/{gig_id}/apply/`` -- a supplier bids for a gig.

    A plain APIView rather than CreateAPIView. The generic view's job is to run
    ``serializer.save()``, and creation here must go through the service so that
    rules 1 and 2 are enforced and the whole thing is one transaction. Bending a
    generic view into calling a service is more code and less clarity than
    writing the four honest lines.

    Note the shape: parse, delegate, serialise the result. No business rule
    appears in this method, and no HTTP concept appears in the service. That
    separation is the whole point of the layering.
    """

    def post(self, request, gig_id: int) -> Response:
        gig = get_object_or_404(Gig, pk=gig_id)

        serializer = ApplyToGigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        application = services.apply_to_gig(gig=gig, **serializer.validated_data)

        return Response(
            ApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class GigApplicationListView(generics.ListAPIView):
    """``GET /api/gigs/{gig_id}/applications/`` -- applications for one gig."""

    serializer_class = ApplicationSerializer

    def get_queryset(self):
        # get_object_or_404 rather than filtering blindly: asking for the
        # applications of a gig that does not exist is a 404, not an empty list.
        # Returning [] would tell a client with a typo in the URL that the gig
        # simply has no applicants, which is a different and wrong answer.
        gig = get_object_or_404(Gig, pk=self.kwargs["gig_id"])
        return Application.objects.filter(gig=gig)
