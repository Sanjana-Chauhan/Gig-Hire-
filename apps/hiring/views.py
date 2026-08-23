"""API endpoints for the hiring workflow."""

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.gigs.models import Gig
from apps.hiring import services
from apps.hiring.filters import ContractFilterSet
from apps.hiring.models import Application, Contract, Review
from apps.hiring.serializers import (
    ApplicationSerializer,
    ApplyToGigSerializer,
    ContractSerializer,
    CreateReviewSerializer,
    ReviewSerializer,
)


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


class AcceptApplicationView(APIView):
    """``POST /api/applications/{application_id}/accept/`` -- creator hires.

    Returns **201 with the created Contract**, not the updated application. A
    new resource genuinely came into existence, and the contract id is what the
    caller needs next -- returning the application would force a second request
    to find it. The specification does not state a response shape; the choice is
    recorded in DECISIONS.md.

    No request body: the application id in the URL identifies everything needed.
    Note that without authentication there is nothing here to verify the caller
    is the gig's creator (open question Q1) -- the endpoint trusts whoever calls
    it, which
    is the single largest gap between this implementation and a real one.
    """

    def post(self, request, application_id: int) -> Response:
        application = get_object_or_404(Application, pk=application_id)
        contract = services.accept_application(application=application)
        return Response(
            ContractSerializer(contract).data,
            status=status.HTTP_201_CREATED,
        )


class RejectApplicationView(APIView):
    """``POST /api/applications/{application_id}/reject/`` -- creator declines.

    Returns **200 with the updated application**, unlike accept's 201: nothing
    was created, an existing resource changed state. Returning the application
    also lets a client confirm the new status without a follow-up request.

    Written out rather than sharing a base class with WithdrawApplicationView.
    The two are nearly identical today and will not stay that way: reject must
    authorise the caller as the gig's creator, withdraw as the supplier who
    applied. A shared view would need a branch on that almost immediately.
    """

    def post(self, request, application_id: int) -> Response:
        application = get_object_or_404(Application, pk=application_id)
        updated = services.reject_application(application=application)
        return Response(ApplicationSerializer(updated).data, status=status.HTTP_200_OK)


class WithdrawApplicationView(APIView):
    """``POST /api/applications/{application_id}/withdraw/`` -- supplier pulls out."""

    def post(self, request, application_id: int) -> Response:
        application = get_object_or_404(Application, pk=application_id)
        updated = services.withdraw_application(application=application)
        return Response(ApplicationSerializer(updated).data, status=status.HTTP_200_OK)


class ContractListView(generics.ListAPIView):
    """``GET /api/contracts/?supplier_id=&creator_id=`` -- list contracts."""

    serializer_class = ContractSerializer
    filterset_class = ContractFilterSet

    # select_related on gig is not for the serializer -- that emits primary keys
    # and touches no related table. It is for the *filter*: ?creator_id= joins
    # through gig, and without this the join is repeated per row when the
    # queryset is evaluated. Present because a query needs it, not by habit.
    queryset = Contract.objects.select_related("gig")


class CompleteContractView(APIView):
    """``POST /api/contracts/{contract_id}/complete/`` -- mark work finished.

    Returns 200 with the updated contract. Note this does not complete the gig:
    that is a separate PATCH, gated on no active contract remaining. See
    interpretation I8 in DECISIONS.md.
    """

    def post(self, request, contract_id: int) -> Response:
        contract = get_object_or_404(Contract, pk=contract_id)
        updated = services.complete_contract(contract=contract)
        return Response(ContractSerializer(updated).data, status=status.HTTP_200_OK)


class ContractReviewView(generics.ListCreateAPIView):
    """``POST`` and ``GET`` on ``/api/contracts/{contract_id}/reviews/``.

    The specification only asks for POST. GET is additive, for the same reason
    the creator endpoints were: an endpoint that writes data with no way to read
    it back is not usable, and rule 9's "one review per reviewer_type" is
    something a client needs to be able to check. Recorded in DECISIONS.md.

    ``create`` is written out rather than left to ``CreateModelMixin`` because
    creation must go through the service, where rule 9's guards live. The
    generic's own flow would call ``serializer.save()`` and bypass them.
    """

    serializer_class = ReviewSerializer

    def get_contract(self) -> Contract:
        return get_object_or_404(Contract, pk=self.kwargs["contract_id"])

    def get_queryset(self):
        # Resolving the contract first means reviews for a nonexistent contract
        # are a 404, not an empty list.
        return Review.objects.filter(contract=self.get_contract())

    def create(self, request, *args, **kwargs) -> Response:
        contract = self.get_contract()

        serializer = CreateReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review = services.create_review(contract=contract, **serializer.validated_data)

        return Response(
            ReviewSerializer(review).data,
            status=status.HTTP_201_CREATED,
        )
