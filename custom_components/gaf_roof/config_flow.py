"""Config flow for GAF Roof."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GafApiClient, GafAuthenticationError, GafConnectionError
from .const import (
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MAX_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
)


class GafConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle setup and reauthentication."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect and validate GAF credentials."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await self._async_validate(user_input)
            if error is None:
                return self.async_create_entry(
                    title="GAF Roof", data=user_input
                )
            errors["base"] = error

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Start credential reauthentication."""
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate replacement credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**self._reauth_entry.data, **user_input}
            error = await self._async_validate(data)
            if error is None:
                return self.async_update_reload_and_abort(
                    self._reauth_entry, data=data
                )
            errors["base"] = error

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME,
                    default=self._reauth_entry.data[CONF_USERNAME],
                ): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=schema, errors=errors
        )

    async def _async_validate(self, data: dict[str, Any]) -> str | None:
        client = GafApiClient(
            async_get_clientsession(self.hass),
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
        )
        try:
            await client.async_get_devices()
        except GafAuthenticationError:
            return "invalid_auth"
        except GafConnectionError:
            return "cannot_connect"
        return None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return GafOptionsFlow()


class GafOptionsFlow(OptionsFlow):
    """Configure polling behavior."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_POLL_INTERVAL, default=current): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL),
                    )
                }
            ),
        )
