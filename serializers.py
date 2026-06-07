from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Scenario, SimulationSession, OODAEntry, CommanderProfile


class CommanderProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    win_rate = serializers.ReadOnlyField()

    class Meta:
        model = CommanderProfile
        fields = ['id', 'username', 'rank', 'callsign', 'total_missions',
                  'victories', 'total_score', 'specialization', 'avg_loop_time',
                  'win_rate', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    commander_profile = CommanderProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'commander_profile']


class ScenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scenario
        fields = '__all__'


class ScenarioListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views - no intel_data spoilers"""
    class Meta:
        model = Scenario
        fields = ['id', 'title', 'description', 'theater', 'difficulty',
                  'time_limit_minutes', 'created_at']


class OODAEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = OODAEntry
        fields = '__all__'
        read_only_fields = ['session', 'timestamp']


class SimulationSessionSerializer(serializers.ModelSerializer):
    ooda_entries = OODAEntrySerializer(many=True, read_only=True)
    scenario_title = serializers.CharField(source='scenario.title', read_only=True)
    scenario_theater = serializers.CharField(source='scenario.theater', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = SimulationSession
        fields = ['id', 'user', 'username', 'scenario', 'scenario_title', 'scenario_theater',
                  'current_phase', 'started_at', 'completed_at', 'score',
                  'outcome', 'after_action_report', 'ooda_entries']
        read_only_fields = ['user', 'started_at']


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=4, write_only=True)
    callsign = serializers.CharField(max_length=50)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', '')
        )
        CommanderProfile.objects.create(
            user=user,
            callsign=validated_data['callsign']
        )
        return user
