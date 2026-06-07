from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.db.models import Avg
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
import random

from .models import Scenario, SimulationSession, OODAEntry, CommanderProfile
from .serializers import (
    ScenarioSerializer, ScenarioListSerializer, SimulationSessionSerializer,
    OODAEntrySerializer, CommanderProfileSerializer, UserSerializer, RegisterSerializer
)


# ─── AUTH VIEWS ────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        login(request, user)
        return Response({
            'message': 'Commander registered. Welcome to the theater.',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)
    if user:
        login(request, user)
        return Response({
            'message': 'Authentication successful.',
            'user': UserSerializer(user).data
        })
    return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({'message': 'Logged out.'})


@api_view(['GET'])
def me_view(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Not authenticated'}, status=401)
    return Response(UserSerializer(request.user).data)


# ─── SCENARIO VIEWS ────────────────────────────────────────────────────────────

class ScenarioViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Scenario.objects.filter(is_active=True)

    def get_serializer_class(self):
        if self.action == 'list':
            return ScenarioListSerializer
        return ScenarioSerializer


# ─── SESSION VIEWS ─────────────────────────────────────────────────────────────

class SimulationSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SimulationSessionSerializer

    def get_queryset(self):
        return SimulationSession.objects.filter(user=self.request.user).order_by('-started_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def advance_phase(self, request, pk=None):
        """Advance the OODA loop to the next phase"""
        session = self.get_object()
        phase_order = ['OBSERVE', 'ORIENT', 'DECIDE', 'ACT']

        if session.current_phase in ['COMPLETE', 'FAILED']:
            return Response({'error': 'Session already ended.'}, status=400)

        current_idx = phase_order.index(session.current_phase)
        if current_idx < len(phase_order) - 1:
            session.current_phase = phase_order[current_idx + 1]
        else:
            # After ACT, either loop back or complete
            loop_count = session.ooda_entries.filter(phase='ACT').count()
            scenario_objectives = session.scenario.objectives
            if loop_count >= len(scenario_objectives):
                session.current_phase = 'COMPLETE'
                session.completed_at = timezone.now()
                session.outcome = 'VICTORY'
                # Update commander stats
                _update_commander_stats(session)
            else:
                session.current_phase = 'OBSERVE'

        session.save()
        return Response(SimulationSessionSerializer(session).data)

    @action(detail=True, methods=['post'])
    def submit_phase_data(self, request, pk=None):
        """Submit data for current OODA phase"""
        session = self.get_object()
        phase = session.current_phase

        if phase in ['COMPLETE', 'FAILED']:
            return Response({'error': 'Session ended.'}, status=400)

        loop_number = session.ooda_entries.values('loop_number').distinct().count() + 1
        # Check if entry for this phase/loop exists
        existing = session.ooda_entries.filter(
            phase=phase, loop_number=loop_number
        ).first()

        data = request.data.copy()
        data['session'] = session.id
        data['phase'] = phase
        data['loop_number'] = loop_number

        # Calculate phase score based on quality of input
        phase_score = _calculate_phase_score(phase, data, session.scenario)
        data['phase_score'] = phase_score

        if existing:
            serializer = OODAEntrySerializer(existing, data=data, partial=True)
        else:
            serializer = OODAEntrySerializer(data=data)

        if serializer.is_valid():
            entry = serializer.save(session=session)
            # Update total score
            session.score = session.ooda_entries.aggregate(
                total=Avg('phase_score'))['total'] or 0
            session.save()
            return Response(OODAEntrySerializer(entry).data)

        return Response(serializer.errors, status=400)

    @action(detail=True, methods=['post'])
    def generate_aar(self, request, pk=None):
        """Generate After Action Report"""
        session = self.get_object()
        entries = session.ooda_entries.all()

        loop_count = entries.values('loop_number').distinct().count()
        avg_score = entries.aggregate(avg=Avg('phase_score'))['avg'] or 0

        aar = f"""AFTER ACTION REPORT
{'='*50}
COMMANDER: {session.user.commander_profile.rank} {session.user.commander_profile.callsign}
SCENARIO: {session.scenario.title}
THEATER: {session.scenario.theater}
OUTCOME: {session.outcome}
FINAL SCORE: {session.score:.0f}/100

OODA LOOP ANALYSIS:
- Total loops completed: {loop_count}
- Average phase score: {avg_score:.1f}/100

PHASE BREAKDOWN:
"""
        for phase in ['OBSERVE', 'ORIENT', 'DECIDE', 'ACT']:
            phase_entries = entries.filter(phase=phase)
            if phase_entries.exists():
                avg = phase_entries.aggregate(avg=Avg('phase_score'))['avg'] or 0
                aar += f"  {phase}: {avg:.0f}/100\n"

        aar += f"""
LESSONS LEARNED:
{_generate_lessons(session, entries)}

END OF REPORT
"""
        session.after_action_report = aar
        session.save()
        return Response({'aar': aar})


# ─── LEADERBOARD ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leaderboard_view(request):
    profiles = CommanderProfile.objects.select_related('user').order_by('-total_score')[:20]
    return Response(CommanderProfileSerializer(profiles, many=True).data)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _calculate_phase_score(phase, data, scenario):
    """Simple scoring heuristic based on completeness of phase data"""
    score = 50  # base score

    if phase == 'OBSERVE':
        intel = data.get('intel_gathered', [])
        if len(intel) >= 3:
            score += 20
        if data.get('observation_notes', ''):
            score += 15
        if len(intel) >= 5:
            score += 15

    elif phase == 'ORIENT':
        if data.get('threat_assessment'):
            score += 20
        if len(data.get('situational_analysis', '')) > 50:
            score += 30

    elif phase == 'DECIDE':
        options = data.get('options_considered', [])
        if len(options) >= 2:
            score += 20
        if data.get('decision_rationale', ''):
            score += 15
        if data.get('chosen_option'):
            score += 15

    elif phase == 'ACT':
        if data.get('action_taken'):
            score += 30
        score += random.randint(-10, 20)  # Fog of war variability

    return min(100, max(0, score))


def _update_commander_stats(session):
    try:
        profile = session.user.commander_profile
        profile.total_missions += 1
        if session.outcome == 'VICTORY':
            profile.victories += 1
        profile.total_score += session.score
        # Update avg loop time
        entries = session.ooda_entries.all()
        if entries.exists():
            avg_time = entries.aggregate(avg=Avg('time_spent_seconds'))['avg'] or 0
            if profile.avg_loop_time == 0:
                profile.avg_loop_time = avg_time
            else:
                profile.avg_loop_time = (profile.avg_loop_time + avg_time) / 2
        # Update rank
        profile.rank = _determine_rank(profile.total_score)
        profile.save()
    except CommanderProfile.DoesNotExist:
        pass


def _determine_rank(score):
    if score < 100: return 'PRIVATE'
    if score < 300: return 'CORPORAL'
    if score < 600: return 'SERGEANT'
    if score < 1000: return 'LIEUTENANT'
    if score < 1500: return 'CAPTAIN'
    if score < 2500: return 'MAJOR'
    if score < 4000: return 'COLONEL'
    return 'GENERAL'


def _generate_lessons(session, entries):
    lessons = []
    obs_entries = entries.filter(phase='OBSERVE')
    if obs_entries.exists():
        avg = obs_entries.aggregate(avg=Avg('phase_score'))['avg'] or 0
        if avg < 60:
            lessons.append("- Observation phase needs improvement. Gather more intelligence before proceeding.")
        else:
            lessons.append("- Strong situational awareness demonstrated in observation phase.")

    dec_entries = entries.filter(phase='DECIDE')
    if dec_entries.exists():
        avg = dec_entries.aggregate(avg=Avg('phase_score'))['avg'] or 0
        if avg < 60:
            lessons.append("- Decision-making could be improved. Consider more options before committing.")
        else:
            lessons.append("- Decision cycles were effective and well-reasoned.")

    if not lessons:
        lessons.append("- Complete all OODA phases for detailed assessment.")

    return '\n'.join(lessons)
