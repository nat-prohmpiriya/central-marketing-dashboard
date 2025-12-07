"""Tests for simple alerts module."""

from datetime import datetime, timezone

import pytest

from src.models.simple_alerts import (
    Alert,
    AlertRule,
    AlertRuleEngine,
    AlertSeverity,
    AlertStatus,
    AlertType,
    DEFAULT_ALERT_RULES,
)


class TestAlertType:
    """Tests for AlertType enum."""

    def test_alert_type_values(self):
        """Test alert type enum values."""
        assert AlertType.LOW_ROAS.value == "low_roas"
        assert AlertType.HIGH_CPA.value == "high_cpa"
        assert AlertType.REVENUE_DROP.value == "revenue_drop"
        assert AlertType.SPEND_ANOMALY.value == "spend_anomaly"
        assert AlertType.LOW_CONVERSION_RATE.value == "low_conversion_rate"
        assert AlertType.HIGH_CANCELLATION_RATE.value == "high_cancellation_rate"


class TestAlertSeverity:
    """Tests for AlertSeverity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertRule:
    """Tests for AlertRule dataclass."""

    def test_rule_creation(self):
        """Test creating an alert rule."""
        rule = AlertRule(
            name="Test Rule",
            alert_type=AlertType.LOW_ROAS,
            condition="ROAS < 2",
            threshold=2.0,
            comparison="lt",
            severity=AlertSeverity.WARNING,
        )

        assert rule.name == "Test Rule"
        assert rule.alert_type == AlertType.LOW_ROAS
        assert rule.threshold == 2.0
        assert rule.comparison == "lt"
        assert rule.enabled is True

    def test_evaluate_less_than(self):
        """Test rule evaluation with less than comparison."""
        rule = AlertRule(
            name="Low ROAS",
            alert_type=AlertType.LOW_ROAS,
            condition="ROAS < 2",
            threshold=2.0,
            comparison="lt",
        )

        assert rule.evaluate(1.5) is True
        assert rule.evaluate(2.0) is False
        assert rule.evaluate(2.5) is False
        assert rule.evaluate(None) is False

    def test_evaluate_greater_than(self):
        """Test rule evaluation with greater than comparison."""
        rule = AlertRule(
            name="High CPA",
            alert_type=AlertType.HIGH_CPA,
            condition="CPA > 300",
            threshold=300.0,
            comparison="gt",
        )

        assert rule.evaluate(350.0) is True
        assert rule.evaluate(300.0) is False
        assert rule.evaluate(250.0) is False

    def test_evaluate_less_than_or_equal(self):
        """Test rule evaluation with lte comparison."""
        rule = AlertRule(
            name="Test",
            alert_type=AlertType.LOW_ROAS,
            condition="value <= 10",
            threshold=10.0,
            comparison="lte",
        )

        assert rule.evaluate(10.0) is True
        assert rule.evaluate(9.0) is True
        assert rule.evaluate(11.0) is False

    def test_evaluate_greater_than_or_equal(self):
        """Test rule evaluation with gte comparison."""
        rule = AlertRule(
            name="Test",
            alert_type=AlertType.HIGH_CPA,
            condition="value >= 100",
            threshold=100.0,
            comparison="gte",
        )

        assert rule.evaluate(100.0) is True
        assert rule.evaluate(101.0) is True
        assert rule.evaluate(99.0) is False

    def test_evaluate_equal(self):
        """Test rule evaluation with equal comparison."""
        rule = AlertRule(
            name="Test",
            alert_type=AlertType.SPEND_ANOMALY,
            condition="value = 0",
            threshold=0.0,
            comparison="eq",
        )

        assert rule.evaluate(0.0) is True
        assert rule.evaluate(0.1) is False

    def test_to_dict(self):
        """Test converting rule to dictionary."""
        rule = AlertRule(
            name="Test Rule",
            alert_type=AlertType.LOW_ROAS,
            condition="ROAS < 2",
            threshold=2.0,
            platforms=["shopee", "lazada"],
        )

        result = rule.to_dict()

        assert result["name"] == "Test Rule"
        assert result["alert_type"] == "low_roas"
        assert result["threshold"] == 2.0
        assert result["platforms"] == ["shopee", "lazada"]


class TestAlert:
    """Tests for Alert dataclass."""

    def test_alert_creation(self):
        """Test creating an alert."""
        now = datetime.now(timezone.utc)
        alert = Alert(
            alert_id="ALERT-001",
            alert_type=AlertType.LOW_ROAS,
            severity=AlertSeverity.WARNING,
            title="Low ROAS: Shopee Campaign",
            message="ROAS is 1.8, below threshold of 2.0",
            metric_name="roas",
            metric_value=1.8,
            threshold=2.0,
            platform="shopee",
            entity_type="campaign",
            entity_id="campaign_123",
            entity_name="Shopee Campaign",
            date=now,
        )

        assert alert.alert_id == "ALERT-001"
        assert alert.alert_type == AlertType.LOW_ROAS
        assert alert.severity == AlertSeverity.WARNING
        assert alert.status == AlertStatus.ACTIVE
        assert alert.metric_value == 1.8

    def test_alert_to_dict(self):
        """Test converting alert to dictionary."""
        now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        alert = Alert(
            alert_id="ALERT-002",
            alert_type=AlertType.HIGH_CPA,
            severity=AlertSeverity.CRITICAL,
            title="High CPA",
            message="CPA is 550 THB",
            metric_name="cpa",
            metric_value=550.0,
            threshold=500.0,
            platform="lazada",
            entity_type="daily",
            entity_id="daily_2024-01-15",
            entity_name="Lazada Daily",
            date=now,
            created_at=now,
        )

        result = alert.to_dict()

        assert result["alert_id"] == "ALERT-002"
        assert result["alert_type"] == "high_cpa"
        assert result["severity"] == "critical"
        assert result["status"] == "active"
        assert result["metric_value"] == 550.0
        assert result["threshold"] == 500.0

    def test_alert_from_dict(self):
        """Test creating alert from dictionary."""
        data = {
            "alert_id": "ALERT-003",
            "alert_type": "revenue_drop",
            "severity": "warning",
            "title": "Revenue Drop",
            "message": "Revenue dropped by 25%",
            "metric_name": "revenue_change_pct",
            "metric_value": -0.25,
            "threshold": -0.20,
            "platform": "tiktok_shop",
            "entity_type": "weekly",
            "entity_id": "weekly_001",
            "entity_name": "TikTok Weekly",
            "date": "2024-01-15T00:00:00+00:00",
            "created_at": "2024-01-15T10:00:00+00:00",
            "status": "active",
            "metadata": {"previous_revenue": 1000000},
        }

        alert = Alert.from_dict(data)

        assert alert.alert_id == "ALERT-003"
        assert alert.alert_type == AlertType.REVENUE_DROP
        assert alert.severity == AlertSeverity.WARNING
        assert alert.metric_value == -0.25
        assert alert.metadata["previous_revenue"] == 1000000


class TestAlertRuleEngine:
    """Tests for AlertRuleEngine class."""

    def test_engine_initialization_with_defaults(self):
        """Test engine initialization with default rules."""
        engine = AlertRuleEngine()

        assert len(engine.rules) == len(DEFAULT_ALERT_RULES)

    def test_engine_initialization_with_custom_rules(self):
        """Test engine initialization with custom rules."""
        custom_rules = [
            AlertRule(
                name="Custom ROAS",
                alert_type=AlertType.LOW_ROAS,
                condition="ROAS < 3",
                threshold=3.0,
            )
        ]
        engine = AlertRuleEngine(rules=custom_rules)

        assert len(engine.rules) == 1
        assert engine.rules[0].threshold == 3.0

    def test_add_rule(self):
        """Test adding a rule to the engine."""
        engine = AlertRuleEngine(rules=[])
        rule = AlertRule(
            name="New Rule",
            alert_type=AlertType.LOW_ROAS,
            condition="ROAS < 1",
            threshold=1.0,
        )

        engine.add_rule(rule)

        assert len(engine.rules) == 1
        assert engine.rules[0].name == "New Rule"

    def test_remove_rule(self):
        """Test removing a rule from the engine."""
        rule = AlertRule(
            name="To Remove",
            alert_type=AlertType.LOW_ROAS,
            condition="ROAS < 1",
            threshold=1.0,
        )
        engine = AlertRuleEngine(rules=[rule])

        result = engine.remove_rule("To Remove")

        assert result is True
        assert len(engine.rules) == 0

    def test_remove_nonexistent_rule(self):
        """Test removing a rule that doesn't exist."""
        engine = AlertRuleEngine(rules=[])

        result = engine.remove_rule("Does Not Exist")

        assert result is False

    def test_get_rules_by_type(self):
        """Test getting rules by alert type."""
        engine = AlertRuleEngine()

        roas_rules = engine.get_rules_by_type(AlertType.LOW_ROAS)
        cpa_rules = engine.get_rules_by_type(AlertType.HIGH_CPA)

        assert len(roas_rules) >= 1
        assert all(r.alert_type == AlertType.LOW_ROAS for r in roas_rules)
        assert len(cpa_rules) >= 1
        assert all(r.alert_type == AlertType.HIGH_CPA for r in cpa_rules)

    def test_evaluate_roas_critical(self):
        """Test evaluating ROAS that triggers critical alert."""
        engine = AlertRuleEngine()
        now = datetime.now(timezone.utc)

        alerts = engine.evaluate_roas(
            roas=1.2,
            platform="shopee",
            entity_type="daily",
            entity_id="daily_001",
            entity_name="Shopee Daily",
            date=now,
        )

        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL
        assert alerts[0].metric_value == 1.2
        assert "1.5" in alerts[0].message

    def test_evaluate_roas_warning(self):
        """Test evaluating ROAS that triggers warning alert."""
        engine = AlertRuleEngine()
        now = datetime.now(timezone.utc)

        alerts = engine.evaluate_roas(
            roas=1.8,
            platform="lazada",
            entity_type="campaign",
            entity_id="campaign_001",
            entity_name="Lazada Campaign",
            date=now,
        )

        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.WARNING
        assert alerts[0].metric_value == 1.8

    def test_evaluate_roas_no_alert(self):
        """Test evaluating ROAS that doesn't trigger alert."""
        engine = AlertRuleEngine()
        now = datetime.now(timezone.utc)

        alerts = engine.evaluate_roas(
            roas=3.5,
            platform="shopee",
            entity_type="daily",
            entity_id="daily_001",
            entity_name="Shopee Daily",
            date=now,
        )

        assert len(alerts) == 0

    def test_evaluate_roas_none(self):
        """Test evaluating None ROAS."""
        engine = AlertRuleEngine()
        now = datetime.now(timezone.utc)

        alerts = engine.evaluate_roas(
            roas=None,
            platform="shopee",
            entity_type="daily",
            entity_id="daily_001",
            entity_name="Shopee Daily",
            date=now,
        )

        assert len(alerts) == 0

    def test_evaluate_cpa_critical(self):
        """Test evaluating high CPA that triggers critical alert."""
        engine = AlertRuleEngine()
        now = datetime.now(timezone.utc)

        alerts = engine.evaluate_cpa(
            cpa=600.0,
            platform="facebook_ads",
            entity_type="campaign",
            entity_id="fb_campaign_001",
            entity_name="FB Campaign",
            date=now,
        )

        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL
        assert "500" in alerts[0].message

    def test_evaluate_cpa_warning(self):
        """Test evaluating CPA that triggers warning."""
        engine = AlertRuleEngine()
        now = datetime.now(timezone.utc)

        alerts = engine.evaluate_cpa(
            cpa=350.0,
            platform="google_ads",
            entity_type="campaign",
            entity_id="g_campaign_001",
            entity_name="Google Campaign",
            date=now,
        )

        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.WARNING

    def test_evaluate_revenue_change_critical(self):
        """Test evaluating revenue drop that triggers critical alert."""
        engine = AlertRuleEngine()
        now = datetime.now(timezone.utc)

        alerts = engine.evaluate_revenue_change(
            revenue_change_pct=-0.35,
            platform="shopee",
            entity_type="weekly",
            entity_id="weekly_001",
            entity_name="Shopee Weekly",
            date=now,
            current_revenue=650000,
            previous_revenue=1000000,
        )

        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL
        assert alerts[0].metadata["current_revenue"] == 650000
        assert alerts[0].metadata["previous_revenue"] == 1000000

    def test_evaluate_revenue_change_warning(self):
        """Test evaluating revenue drop that triggers warning."""
        engine = AlertRuleEngine()
        now = datetime.now(timezone.utc)

        alerts = engine.evaluate_revenue_change(
            revenue_change_pct=-0.22,
            platform="lazada",
            entity_type="weekly",
            entity_id="weekly_001",
            entity_name="Lazada Weekly",
            date=now,
        )

        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.WARNING

    def test_evaluate_conversion_rate(self):
        """Test evaluating low conversion rate."""
        engine = AlertRuleEngine()
        now = datetime.now(timezone.utc)

        alerts = engine.evaluate_conversion_rate(
            conversion_rate=0.005,
            platform="shopee",
            entity_type="campaign",
            entity_id="campaign_001",
            entity_name="Shopee Campaign",
            date=now,
        )

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.LOW_CONVERSION_RATE
        assert "0.50%" in alerts[0].message

    def test_evaluate_cancellation_rate(self):
        """Test evaluating high cancellation rate."""
        engine = AlertRuleEngine()
        now = datetime.now(timezone.utc)

        alerts = engine.evaluate_cancellation_rate(
            cancellation_rate=0.20,
            platform="lazada",
            entity_type="shop",
            entity_id="shop_001",
            entity_name="Lazada Shop",
            date=now,
        )

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.HIGH_CANCELLATION_RATE
        assert "20.0%" in alerts[0].message

    def test_evaluate_all(self):
        """Test evaluating all metrics at once."""
        engine = AlertRuleEngine()
        now = datetime.now(timezone.utc)

        metrics = {
            "roas": 1.3,  # Should trigger critical
            "cpa": 350,  # Should trigger warning
            "conversion_rate": 0.02,  # Should not trigger (above 1%)
        }

        alerts = engine.evaluate_all(
            metrics=metrics,
            platform="shopee",
            entity_type="daily",
            entity_id="daily_001",
            entity_name="Shopee Daily",
            date=now,
        )

        assert len(alerts) == 2
        alert_types = {a.alert_type for a in alerts}
        assert AlertType.LOW_ROAS in alert_types
        assert AlertType.HIGH_CPA in alert_types

    def test_platform_filter(self):
        """Test that platform filter works correctly."""
        rule = AlertRule(
            name="Shopee Only",
            alert_type=AlertType.LOW_ROAS,
            condition="ROAS < 2",
            threshold=2.0,
            platforms=["shopee"],
        )
        engine = AlertRuleEngine(rules=[rule])
        now = datetime.now(timezone.utc)

        # Should trigger for shopee
        shopee_alerts = engine.evaluate_roas(
            roas=1.5,
            platform="shopee",
            entity_type="daily",
            entity_id="daily_001",
            entity_name="Shopee Daily",
            date=now,
        )
        assert len(shopee_alerts) == 1

        # Should not trigger for lazada
        lazada_alerts = engine.evaluate_roas(
            roas=1.5,
            platform="lazada",
            entity_type="daily",
            entity_id="daily_001",
            entity_name="Lazada Daily",
            date=now,
        )
        assert len(lazada_alerts) == 0

    def test_unique_alert_ids(self):
        """Test that alert IDs are unique."""
        engine = AlertRuleEngine()
        now = datetime.now(timezone.utc)

        # Generate multiple alerts
        alerts1 = engine.evaluate_roas(
            roas=1.2, platform="shopee", entity_type="daily",
            entity_id="d1", entity_name="Test1", date=now,
        )
        alerts2 = engine.evaluate_cpa(
            cpa=600, platform="lazada", entity_type="daily",
            entity_id="d2", entity_name="Test2", date=now,
        )

        all_ids = [a.alert_id for a in alerts1 + alerts2]
        assert len(all_ids) == len(set(all_ids))  # All unique


class TestDefaultAlertRules:
    """Tests for default alert rules configuration."""

    def test_default_rules_exist(self):
        """Test that default rules are defined."""
        assert len(DEFAULT_ALERT_RULES) > 0

    def test_default_rules_have_required_fields(self):
        """Test that all default rules have required fields."""
        for rule in DEFAULT_ALERT_RULES:
            assert rule.name is not None
            assert rule.alert_type is not None
            assert rule.condition is not None
            assert rule.threshold is not None
            assert rule.comparison in ("lt", "gt", "lte", "gte", "eq")
            assert rule.severity is not None

    def test_roas_rules_exist(self):
        """Test that ROAS rules are defined."""
        roas_rules = [r for r in DEFAULT_ALERT_RULES if r.alert_type == AlertType.LOW_ROAS]
        assert len(roas_rules) >= 2  # Critical and warning

    def test_cpa_rules_exist(self):
        """Test that CPA rules are defined."""
        cpa_rules = [r for r in DEFAULT_ALERT_RULES if r.alert_type == AlertType.HIGH_CPA]
        assert len(cpa_rules) >= 2  # Critical and warning

    def test_revenue_rules_exist(self):
        """Test that revenue drop rules are defined."""
        revenue_rules = [r for r in DEFAULT_ALERT_RULES if r.alert_type == AlertType.REVENUE_DROP]
        assert len(revenue_rules) >= 2  # Critical and warning
