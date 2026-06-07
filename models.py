from django.db import models
from django.contrib.auth.models import User
import json


class Scenario(models.Model):
    DIFFICULTY_CHOICES = [
        ('NOVICE', 'Novice'),
        ('OPERATOR', 'Operator'),
        ('COMMANDER', 'Commander'),
        ('STRATEGIC', 'Strategic'),
    ]
    THEATER_CHOICES = [
        ('LAND', 'Land'),
        ('SEA', 'Sea'),
        ('AIR', 'Air'),
        ('CYBER', 'Cyber'),
        ('HYBRID', 'Hybrid'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    theater = models.CharField(max_length=20, choices=THEATER_CHOICES)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    briefing = models.TextField()
    intel_data = models.JSONField(default=dict)  # Enemy positions, assets, etc.
    objectives = models.JSONField(default=list)
    time_limit_minutes = models.IntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.theater}] {self.title}"


class SimulationSession(models.Model):
    STATUS_CHOICES = [
        ('OBSERVE', 'Observe'),
        ('ORIENT', 'Orient'),
        ('DECIDE', 'Decide'),
        ('ACT', 'Act'),
        ('COMPLETE', 'Complete'),
        ('FAILED', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='sessions')
    current_phase = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OBSERVE')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(default=0)
    outcome = models.CharField(max_length=50, blank=True)  # VICTORY / DEFEAT / PARTIAL
    after_action_report = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.username} - {self.scenario.title} [{self.current_phase}]"


class OODAEntry(models.Model):
    """Each completed OODA loop cycle in a session"""
    PHASE_CHOICES = [
        ('OBSERVE', 'Observe'),
        ('ORIENT', 'Orient'),
        ('DECIDE', 'Decide'),
        ('ACT', 'Act'),
    ]

    session = models.ForeignKey(SimulationSession, on_delete=models.CASCADE, related_name='ooda_entries')
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES)
    loop_number = models.IntegerField(default=1)

    # Observe phase
    intel_gathered = models.JSONField(default=list)  # List of intel items selected
    observation_notes = models.TextField(blank=True)

    # Orient phase
    threat_assessment = models.CharField(max_length=50, blank=True)
    situational_analysis = models.TextField(blank=True)
    mental_model = models.JSONField(default=dict)

    # Decide phase
    chosen_option = models.CharField(max_length=200, blank=True)
    decision_rationale = models.TextField(blank=True)
    options_considered = models.JSONField(default=list)

    # Act phase
    action_taken = models.CharField(max_length=200, blank=True)
    action_result = models.JSONField(default=dict)
    phase_score = models.IntegerField(default=0)

    timestamp = models.DateTimeField(auto_now_add=True)
    time_spent_seconds = models.IntegerField(default=0)

    class Meta:
        ordering = ['loop_number', 'timestamp']

    def __str__(self):
        return f"Loop {self.loop_number} | {self.phase} | Session {self.session_id}"


class CommanderProfile(models.Model):
    RANK_CHOICES = [
        ('PRIVATE', 'Private'),
        ('CORPORAL', 'Corporal'),
        ('SERGEANT', 'Sergeant'),
        ('LIEUTENANT', 'Lieutenant'),
        ('CAPTAIN', 'Captain'),
        ('MAJOR', 'Major'),
        ('COLONEL', 'Colonel'),
        ('GENERAL', 'General'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='commander_profile')
    rank = models.CharField(max_length=20, choices=RANK_CHOICES, default='PRIVATE')
    callsign = models.CharField(max_length=50)
    total_missions = models.IntegerField(default=0)
    victories = models.IntegerField(default=0)
    total_score = models.IntegerField(default=0)
    specialization = models.CharField(max_length=50, blank=True)  # LAND, SEA, etc.
    avg_loop_time = models.FloatField(default=0)  # Average seconds per OODA loop
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def win_rate(self):
        if self.total_missions == 0:
            return 0
        return round((self.victories / self.total_missions) * 100, 1)

    def __str__(self):
        return f"{self.rank} {self.callsign} ({self.user.username})"
