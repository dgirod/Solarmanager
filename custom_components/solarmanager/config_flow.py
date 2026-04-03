"""Config flow for the Solar Manager integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api.client import SolarManagerAuthError, SolarManagerApiError, SolarManagerClient
from .const import CONF_SMART_MANAGER_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Schema helpers
# -----------------------------------------------------------------------

def _build_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return a vol.Schema with optional pre-filled defaults."""
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=d.get(CONF_NAME, "Solar Manager")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
            vol.Required(CONF_USERNAME, default=d.get(CONF_USERNAME, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
            ),
            vol.Required(CONF_PASSWORD, default=d.get(CONF_PASSWORD, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
            ),
            vol.Required(CONF_SMART_MANAGER_ID, default=d.get(CONF_SMART_MANAGER_ID, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="off")
            ),
        }
    )


# -----------------------------------------------------------------------
# Credential validation
# -----------------------------------------------------------------------

async def _validate_credentials(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, str]:
    """Test credentials against the API and return an errors dict (empty = OK)."""
    session = async_get_clientsession(hass)
    client = SolarManagerClient(
        session,
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        data[CONF_SMART_MANAGER_ID],
    )
    errors: dict[str, str] = {}
    try:
        valid = await client.validate_credentials()
        if not valid:
            errors["base"] = "invalid_auth"
    except SolarManagerAuthError:
        errors["base"] = "invalid_auth"
    except SolarManagerApiError:
        errors["base"] = "cannot_connect"
    except Exception:
        _LOGGER.exception("Unexpected error during credential validation")
        errors["base"] = "unknown"
    return errors


# -----------------------------------------------------------------------
# Config flow
# -----------------------------------------------------------------------

class SolarManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solar Manager."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SolarManagerOptionsFlow:
        """Return the options flow handler."""
        return SolarManagerOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial setup step shown to the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Prevent duplicate entries for the same gateway
            await self.async_set_unique_id(user_input[CONF_SMART_MANAGER_ID])
            self._abort_if_unique_id_configured()

            errors = await _validate_credentials(self.hass, user_input)
            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                    options=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(user_input),
            description_placeholders={
                "smid_help": "Zu finden in solarmanager.ch → Einstellungen (Format: SM-XXXXXX)",
                "docs_url": "https://github.com/dgirod/Solarmanager",
            },
            errors=errors,
        )


# -----------------------------------------------------------------------
# Options flow (re-configure after initial setup)
# -----------------------------------------------------------------------

class SolarManagerOptionsFlow(config_entries.OptionsFlow):
    """Allow the user to update credentials after initial setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await _validate_credentials(self.hass, user_input)
            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        # Pre-fill with current values
        current = dict(self.config_entry.options or self.config_entry.data)

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(user_input or current),
            description_placeholders={
                "smid_help": "Zu finden in solarmanager.ch → Einstellungen (Format: SM-XXXXXX)",
            },
            errors=errors,
        )
