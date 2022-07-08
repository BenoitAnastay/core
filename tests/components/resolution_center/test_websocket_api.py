"""Test the resolution center websocket API."""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.resolution_center import (
    ResolutionCenterFlow,
    async_create_issue,
)
from homeassistant.components.resolution_center.const import DOMAIN
from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component

from tests.common import mock_platform


class MockFixFlow(ResolutionCenterFlow):
    """Handler for an issue fixing flow."""

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of a fix flow."""

        return await (self.async_step_confirm())

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the confirm step of a fix flow."""
        if user_input is not None:
            return self.async_create_entry(title=None, data=None)

        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}))


@pytest.fixture(autouse=True)
async def mock_resolution_center_integration(hass):
    """Mock a resolution_center integration."""
    hass.config.components.add("fake_integration")
    hass.config.components.add("integration_without_diagnostics")

    def async_create_fix_flow(hass, issue_id):
        if issue_id != "issue_1":
            raise HomeAssistantError
        return MockFixFlow()

    mock_platform(
        hass,
        "fake_integration.resolution_center",
        Mock(async_create_fix_flow=AsyncMock(wraps=async_create_fix_flow)),
    )
    mock_platform(
        hass,
        "integration_without_diagnostics.resolution_center",
        Mock(spec=[]),
    )


async def test_dismiss_issue(hass: HomeAssistant, hass_ws_client) -> None:
    """Test we can dismiss an issue."""
    assert await async_setup_component(hass, DOMAIN, {})

    client = await hass_ws_client(hass)

    issues = [
        {
            "breaks_in_ha_version": "2022.9",
            "domain": "test",
            "issue_id": "issue_1",
            "is_fixable": True,
            "learn_more_url": "https://theuselessweb.com",
            "severity": "error",
            "translation_key": "abc_123",
            "translation_placeholders": {"abc": "123"},
        },
    ]

    for issue in issues:
        async_create_issue(
            hass,
            issue["domain"],
            issue["issue_id"],
            breaks_in_ha_version=issue["breaks_in_ha_version"],
            is_fixable=issue["is_fixable"],
            learn_more_url=issue["learn_more_url"],
            severity=issue["severity"],
            translation_key=issue["translation_key"],
            translation_placeholders=issue["translation_placeholders"],
        )

    await client.send_json({"id": 1, "type": "resolution_center/list_issues"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == {
        "issues": [
            dict(
                issue,
                dismissed=False,
                dismissed_version=None,
            )
            for issue in issues
        ]
    }

    await client.send_json(
        {
            "id": 2,
            "type": "resolution_center/dismiss_issue",
            "domain": "test",
            "issue_id": "no_such_issue",
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]

    await client.send_json(
        {
            "id": 3,
            "type": "resolution_center/dismiss_issue",
            "domain": "test",
            "issue_id": "issue_1",
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] is None

    await client.send_json({"id": 4, "type": "resolution_center/list_issues"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == {
        "issues": [
            dict(
                issue,
                dismissed=True,
                dismissed_version=ha_version,
            )
            for issue in issues
        ]
    }


async def test_fix_non_existing_issue(hass: HomeAssistant, hass_ws_client) -> None:
    """Test trying to fix an issue that doesn't exist."""
    assert await async_setup_component(hass, DOMAIN, {})

    client = await hass_ws_client(hass)

    issues = [
        {
            "breaks_in_ha_version": "2022.9",
            "domain": "fake_integration",
            "issue_id": "issue_1",
            "is_fixable": True,
            "learn_more_url": "https://theuselessweb.com",
            "severity": "error",
            "translation_key": "abc_123",
            "translation_placeholders": {"abc": "123"},
        },
    ]

    for issue in issues:
        async_create_issue(
            hass,
            issue["domain"],
            issue["issue_id"],
            breaks_in_ha_version=issue["breaks_in_ha_version"],
            is_fixable=issue["is_fixable"],
            learn_more_url=issue["learn_more_url"],
            severity=issue["severity"],
            translation_key=issue["translation_key"],
            translation_placeholders=issue["translation_placeholders"],
        )

    await client.send_json({"id": 1, "type": "resolution_center/list_issues"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == {
        "issues": [
            dict(
                issue,
                dismissed=False,
                dismissed_version=None,
            )
            for issue in issues
        ]
    }

    await client.send_json(
        {
            "id": 2,
            "type": "resolution_center/fix_issue",
            "domain": "fake_integration",
            "issue_id": "no_such_issue",
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]

    await client.send_json({"id": 3, "type": "resolution_center/list_issues"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == {
        "issues": [
            dict(
                issue,
                dismissed=False,
                dismissed_version=None,
            )
            for issue in issues
        ]
    }


async def test_fix_issue(hass: HomeAssistant, hass_ws_client) -> None:
    """Test we can fix an issue."""
    assert await async_setup_component(hass, DOMAIN, {})

    client = await hass_ws_client(hass)

    issues = [
        {
            "breaks_in_ha_version": "2022.9",
            "domain": "fake_integration",
            "issue_id": "issue_1",
            "is_fixable": True,
            "learn_more_url": "https://theuselessweb.com",
            "severity": "error",
            "translation_key": "abc_123",
            "translation_placeholders": {"abc": "123"},
        },
    ]

    for issue in issues:
        async_create_issue(
            hass,
            issue["domain"],
            issue["issue_id"],
            breaks_in_ha_version=issue["breaks_in_ha_version"],
            is_fixable=issue["is_fixable"],
            learn_more_url=issue["learn_more_url"],
            severity=issue["severity"],
            translation_key=issue["translation_key"],
            translation_placeholders=issue["translation_placeholders"],
        )

    await client.send_json({"id": 1, "type": "resolution_center/list_issues"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == {
        "issues": [
            dict(
                issue,
                dismissed=False,
                dismissed_version=None,
            )
            for issue in issues
        ]
    }

    await client.send_json(
        {
            "id": 2,
            "type": "resolution_center/fix_issue",
            "domain": "fake_integration",
            "issue_id": "issue_1",
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"]["type"] == "form"
    assert msg["result"]["step_id"] == "confirm"

    await client.send_json(
        {
            "id": 3,
            "type": "resolution_center/fix_issue_confirm",
            "flow_id": msg["result"]["flow_id"],
            "user_input": {},
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"]["type"] == "create_entry"

    await client.send_json({"id": 4, "type": "resolution_center/list_issues"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == {"issues": []}


async def test_list_issues(hass: HomeAssistant, hass_ws_client) -> None:
    """Test we can list issues."""
    assert await async_setup_component(hass, DOMAIN, {})

    client = await hass_ws_client(hass)

    await client.send_json({"id": 1, "type": "resolution_center/list_issues"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == {"issues": []}

    issues = [
        {
            "breaks_in_ha_version": "2022.9",
            "domain": "test",
            "is_fixable": True,
            "issue_id": "issue_1",
            "learn_more_url": "https://theuselessweb.com",
            "severity": "error",
            "translation_key": "abc_123",
            "translation_placeholders": {"abc": "123"},
        },
        {
            "breaks_in_ha_version": "2022.8",
            "domain": "test",
            "is_fixable": False,
            "issue_id": "issue_2",
            "learn_more_url": "https://theuselessweb.com/abc",
            "severity": "other",
            "translation_key": "even_worse",
            "translation_placeholders": {"def": "456"},
        },
    ]

    for issue in issues:
        async_create_issue(
            hass,
            issue["domain"],
            issue["issue_id"],
            breaks_in_ha_version=issue["breaks_in_ha_version"],
            is_fixable=issue["is_fixable"],
            learn_more_url=issue["learn_more_url"],
            severity=issue["severity"],
            translation_key=issue["translation_key"],
            translation_placeholders=issue["translation_placeholders"],
        )

    await client.send_json({"id": 2, "type": "resolution_center/list_issues"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == {
        "issues": [
            dict(
                issue,
                dismissed=False,
                dismissed_version=None,
            )
            for issue in issues
        ]
    }
