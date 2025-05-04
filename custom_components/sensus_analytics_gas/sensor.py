"""Sensor platform for the Sensus Analytics Integration."""

from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DEFAULT_NAME, DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the Sensus Analytics sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    currency = hass.config.currency
    sensors = [
        SensusAnalyticsDailyUsageSensor(coordinator, entry),
        SensusAnalyticsUsageUnitSensor(coordinator, entry),
        SensusAnalyticsMeterAddressSensor(coordinator, entry),
        SensusAnalyticsLastReadSensor(coordinator, entry),
        SensusAnalyticsMeterLongitudeSensor(coordinator, entry),
        SensusAnalyticsMeterIdSensor(coordinator, entry),
        SensusAnalyticsMeterLatitudeSensor(coordinator, entry),
        MeterOdometerSensor(coordinator, entry),
        SensusAnalyticsBillingUsageSensor(coordinator, entry),
        SensusAnalyticsBillingCostSensor(coordinator, entry, currency),
        SensusAnalyticsDailyFeeSensor(coordinator, entry, currency),
        LastHourUsageSensor(coordinator, entry),
        LastHourTemperatureSensor(coordinator, entry),
        LastHourTimestampSensor(coordinator, entry),
    ]
    async_add_entities(sensors, True)


# pylint: disable=too-few-public-methods
class UsageConversionMixin:
    """Mixin to provide usage conversion."""

    # pylint: disable=too-many-return-statements
    def _convert_usage(self, usage, usage_unit=None):
        """Convert usage based on configuration and native unit."""
        if usage is None:
            return None
        if usage_unit is None:
            usage_unit = self.coordinator.data.get("usageUnit")

        config_unit_type = self.coordinator.config_entry.data.get("gas_unit_type")

        CCF2THERM = self.coordinator.config_entry.data.get("gas_heat_content_factor")

        if usage_unit == "CCF" and config_unit_type == "Therm":
            try:
                return round(float(usage) * CCF2THERM)
            except (ValueError, TypeError):
                return None
        elif usage_unit == "Therm" and config_unit_type == "CCF":
            try:
                return round(float(usage) / CCF2THERM)
            except (ValueError, TypeError):
                return None
        return usage

    def _get_usage_unit(self):
        """Determine the unit of measurement for usage sensors."""
        usage_unit = self.coordinator.data.get("usageUnit")
        config_unit_type = self.coordinator.config_entry.data.get("unit_type")

        if usage_unit == "CCF" and config_unit_type == "Therm":
            return "Therm"
        if usage_unit == "Therm" and config_unit_type == "CCF":
            return "CCF"
        return usage_unit


class DynamicUnitSensorBase(UsageConversionMixin, CoordinatorEntity, SensorEntity):
    """Base class for sensors with dynamic units."""

    def __init__(self, coordinator, entry):
        """Initialize the dynamic unit sensor base."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.entry = entry
        self._unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Unknown",
            model="Gas Utility Meter",
        )

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._get_usage_unit()


class StaticUnitSensorBase(UsageConversionMixin, CoordinatorEntity, SensorEntity):
    """Base class for sensors with static units."""

    def __init__(self, coordinator, entry, unit=None, device_class=None):
        """Initialize the static unit sensor base."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.entry = entry
        self._unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Unknown",
            model="Gas Utility Meter",
        )
        if unit:
            self._attr_native_unit_of_measurement = unit
        if device_class:
            self._attr_device_class = device_class


class SensusAnalyticsDailyUsageSensor(DynamicUnitSensorBase):
    """Representation of the daily usage sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the daily usage sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Daily Usage"
        self._attr_unique_id = f"{self._unique_id}_daily_usage"
        self._attr_icon = "mdi:gas-burner"
        self._attr_device_class = SensorDeviceClass.GAS
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def last_reset(self):
        """Return the last reset time for the daily usage sensor."""
        return dt_util.start_of_local_day()

    @property
    def native_value(self):
        """Return the state of the sensor."""
        daily_usage = self.coordinator.data.get("dailyUsage")
        return self._convert_usage(daily_usage)


class SensusAnalyticsUsageUnitSensor(StaticUnitSensorBase):
    """Representation of the usage unit sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the usage unit sensor."""
        super().__init__(coordinator, entry, unit=None)
        self._attr_name = f"{DEFAULT_NAME} Native Usage Unit"
        self._attr_unique_id = f"{self._unique_id}_usage_unit"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("usageUnit")


class SensusAnalyticsMeterAddressSensor(StaticUnitSensorBase):
    """Representation of the meter address sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the meter address sensor."""
        super().__init__(coordinator, entry, unit=None)
        self._attr_name = f"{DEFAULT_NAME} Meter Address"
        self._attr_unique_id = f"{self._unique_id}_meter_address"
        self._attr_icon = "mdi:map-marker"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterAddress1")


class SensusAnalyticsLastReadSensor(StaticUnitSensorBase):
    """Representation of the last read timestamp sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the last read sensor."""
        super().__init__(
            coordinator,
            entry,
            unit=None,
            device_class=SensorDeviceClass.TIMESTAMP,
        )
        self._attr_name = f"{DEFAULT_NAME} Last Read"
        self._attr_unique_id = f"{self._unique_id}_last_read"
        self._attr_icon = "mdi:clock-time-nine"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        last_read_ts = self.coordinator.data.get("lastRead")
        if last_read_ts:
            # Convert milliseconds to seconds for timestamp
            try:
                return dt_util.utc_from_timestamp(last_read_ts / 1000)
            except (ValueError, TypeError):
                return None
        return None


class SensusAnalyticsMeterLongitudeSensor(StaticUnitSensorBase):
    """Representation of the meter longitude sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the meter longitude sensor."""
        super().__init__(coordinator, entry, unit="°")
        self._attr_name = f"{DEFAULT_NAME} Meter Longitude"
        self._attr_unique_id = f"{self._unique_id}_meter_longitude"
        self._attr_icon = "mdi:longitude"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterLong")


class SensusAnalyticsMeterIdSensor(StaticUnitSensorBase):
    """Representation of the meter ID sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the meter ID sensor."""
        super().__init__(coordinator, entry, unit=None)
        self._attr_name = f"{DEFAULT_NAME} Meter ID"
        self._attr_unique_id = f"{self._unique_id}_meter_id"
        self._attr_icon = "mdi:account"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterId")


class SensusAnalyticsMeterLatitudeSensor(StaticUnitSensorBase):
    """Representation of the meter latitude sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the meter latitude sensor."""
        super().__init__(coordinator, entry, unit="°")
        self._attr_name = f"{DEFAULT_NAME} Meter Latitude"
        self._attr_unique_id = f"{self._unique_id}_meter_latitude"
        self._attr_icon = "mdi:latitude"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("meterLat")


class MeterOdometerSensor(DynamicUnitSensorBase):
    """Representation of the meter odometer sensor (previously latest read usage)."""

    def __init__(self, coordinator, entry):
        """Initialize the meter odometer sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Meter Odometer"
        self._attr_unique_id = f"{self._unique_id}_meter_odometer"
        self._attr_icon = "mdi:gas-burner"
        self._attr_device_class = SensorDeviceClass.GAS
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def last_reset(self):
        """Return the last reset time for the meter odometer sensor."""
        return None  # Odometer typically does not reset

    @property
    def native_value(self):
        """Return the state of the sensor."""
        latest_read_usage = self.coordinator.data.get("latestReadUsage")
        return self._convert_usage(latest_read_usage)


class SensusAnalyticsBillingUsageSensor(DynamicUnitSensorBase):
    """Representation of the billing usage sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the billing usage sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Billing Usage"
        self._attr_unique_id = f"{self._unique_id}_billing_usage"
        self._attr_icon = "mdi:gas-burner"
        self._attr_device_class = SensorDeviceClass.GAS
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def last_reset(self):
        """Return the last reset time for the billing usage sensor."""
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
        now = datetime.now(local_tz)
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        billing_usage = self.coordinator.data.get("billingUsage")
        return self._convert_usage(billing_usage)


class SensusAnalyticsBillingCostSensor(StaticUnitSensorBase):
    """Representation of the billing cost sensor."""

    def __init__(self, coordinator, entry, currency):
        """Initialize the billing cost sensor."""
        super().__init__(coordinator, entry, unit=currency)
        self._attr_name = f"{DEFAULT_NAME} Billing Cost"
        self._attr_unique_id = f"{self._unique_id}_billing_cost"
        self._attr_icon = "mdi:currency-usd"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        usage = self.coordinator.data.get("billingUsage")
        if usage is None:
            return None
        usage_therm = self._convert_usage(usage)
        return self._calculate_gas_cost(usage_therm)

    def _calculate_gas_cost(self, usage_therm):
        """Calculate the billing cost based on tiers and service fee."""
        gas_fixed_price = self.coordinator.config_entry.data.get("gas_commodity_fixed_price")
        gas_variable_price = self.coordinator.config_entry.data.get("gas_commodity_variable_price") or 0
        gas_service_fee = self.coordinator.config_entry.data.get("gas_service_fee")

        cost = gas_service_fee
        if usage_therm is not None:
            cost += usage_therm * (gas_fixed_price + gas_variable_price)
        return round(cost, 2)


class SensusAnalyticsDailyFeeSensor(StaticUnitSensorBase):
    """Representation of the daily fee sensor."""

    def __init__(self, coordinator, entry, currency):
        """Initialize the daily fee sensor."""
        super().__init__(coordinator, entry, unit=currency)
        self._attr_name = f"{DEFAULT_NAME} Daily Fee"
        self._attr_unique_id = f"{self._unique_id}_daily_fee"
        self._attr_icon = "mdi:currency-usd"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        usage = self.coordinator.data.get("dailyUsage")
        if usage is None:
            return None
        usage_therm = self._convert_usage(usage)
        return self._calculate_daily_gas_fee(usage_therm)

    def _calculate_daily_gas_fee(self, usage_therm):
        """Calculate the daily fee."""
        gas_fixed_price = self.coordinator.config_entry.data.get("gas_commodity_fixed_price")
        gas_variable_price = self.coordinator.config_entry.data.get("gas_commodity_variable_price") or 0

        cost = 0
        if usage_therm is not None:
            cost += usage_therm * (gas_fixed_price + gas_variable_price)
        return round(cost, 2)


class LastHourUsageSensor(DynamicUnitSensorBase):
    """Representation of the last hour usage sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the last hour usage sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = f"{DEFAULT_NAME} Last Hour Usage"
        self._attr_unique_id = f"{self._unique_id}_last_hour_gas_usage"
        self._attr_icon = "mdi:gas-burner"
        self._attr_device_class = SensorDeviceClass.GAS
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def last_reset(self):
        """Return the last reset time for the last hour usage sensor."""
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
        now = datetime.now(local_tz)
        return now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)

    @property
    def native_value(self):
        """Return the usage for the current hour from the previous day."""
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
        now = datetime.now(local_tz)
        target_hour = now.hour
        hourly_data = self.coordinator.data.get("hourly_usage_data", [])
        if not hourly_data:
            return None

        # Find the data corresponding to target_hour from the previous day
        for entry in hourly_data:
            entry_time = dt_util.utc_from_timestamp(entry["timestamp"] / 1000).astimezone(local_tz)
            if entry_time.hour == target_hour:
                usage = entry["usage"]
                usage_unit = entry.get("usage_unit")
                return self._convert_usage(usage, usage_unit)
        return None


class LastHourTemperatureSensor(StaticUnitSensorBase):
    """Representation of the last hour temperature sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the last hour temperature sensor."""
        super().__init__(coordinator, entry, unit="°F")
        self._attr_name = f"{DEFAULT_NAME} Last Hour Temperature"
        self._attr_unique_id = f"{self._unique_id}_last_hour_temperature"
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self):
        """Return the temperature for the current hour from the previous day."""
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
        now = datetime.now(local_tz)
        target_hour = now.hour
        hourly_data = self.coordinator.data.get("hourly_usage_data", [])
        if not hourly_data:
            return None

        for entry in hourly_data:
            entry_time = dt_util.utc_from_timestamp(entry["timestamp"] / 1000).astimezone(local_tz)
            if entry_time.hour == target_hour:
                temp = entry["temp"]
                return temp
        return None


class LastHourTimestampSensor(StaticUnitSensorBase):
    """Representation of the last hour timestamp sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the last hour timestamp sensor."""
        super().__init__(coordinator, entry, unit=None)
        self._attr_name = f"{DEFAULT_NAME} Last Hour Timestamp"
        self._attr_unique_id = f"{self._unique_id}_last_hour_timestamp"
        self._attr_icon = "mdi:clock-time-nine"

    @property
    def native_value(self):
        """Return the timestamp for the current hour's data from the previous day."""
        local_tz = dt_util.get_time_zone(self.hass.config.time_zone)
        now = datetime.now(local_tz)
        target_hour = now.hour
        hourly_data = self.coordinator.data.get("hourly_usage_data", [])
        if not hourly_data:
            return None

        for entry in hourly_data:
            entry_timestamp_ms = entry["timestamp"]
            entry_time = dt_util.utc_from_timestamp(entry_timestamp_ms / 1000).astimezone(local_tz)
            if entry_time.hour == target_hour:
                # Return the timestamp as a formatted string
                return entry_time.strftime("%Y-%m-%d %H:%M:%S")
        return None
