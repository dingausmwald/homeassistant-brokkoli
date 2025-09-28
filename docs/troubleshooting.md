# Troubleshooting

This document provides troubleshooting information for common issues with the Brokkoli Plant Manager integration.

## Installation Issues

### Integration Not Appearing in HACS
**Problem**: The Brokkoli Plant Manager integration doesn't appear in HACS custom repositories.

**Solutions**:
1. Verify that you've added the correct repository URL: `https://github.com/dingausmwald/homeassistant-brokkoli`
2. Ensure the category is set to "Integration" when adding the custom repository
3. Refresh the HACS repository list by clicking the menu (three dots) and selecting "Reload"
4. Check that you're using a supported version of HACS
5. Restart Home Assistant after adding the repository

### Integration Not Loading
**Problem**: The integration appears in HACS but fails to load or install.

**Solutions**:
1. Check Home Assistant logs for error messages related to the plant integration
2. Verify that all required dependencies are installed (recorder, seedfinder, integration, utility_meter, diagnostics)
3. Ensure you're running a compatible version of Home Assistant (2024.8 or later)
4. Clear browser cache and refresh the Home Assistant interface
5. Try reinstalling the integration

### Manual Installation Problems
**Problem**: Manual installation of the integration fails.

**Solutions**:
1. Verify that the `custom_components/plant/` directory is correctly placed in your Home Assistant configuration directory
2. Check that all files were copied correctly without corruption
3. Ensure proper file permissions for the custom_components directory
4. Restart Home Assistant completely after copying files
5. Check logs for import errors or missing files

## Configuration Issues

### Plant Creation Fails
**Problem**: Unable to create a new plant through the configuration flow.

**Solutions**:
1. Verify that all required fields are filled in (name, strain)
2. Check that the selected sensors are valid and available in Home Assistant
3. Ensure that no special characters are used in plant names that might cause issues
4. Check Home Assistant logs for specific error messages
5. Try creating a plant with minimal configuration first, then add sensors

### Sensor Assignment Problems
**Problem**: Sensors are not updating or showing incorrect values.

**Solutions**:
1. Verify that the selected sensors are working correctly in Home Assistant
2. Check that sensor units match expected values (temperature in °C or °F, moisture in %, etc.)
3. Ensure sensors are updating regularly and not showing as "unavailable"
4. Try reassigning sensors through the plant configuration interface
5. Check that sensors are not being filtered or modified by other automations

### Threshold Configuration Issues
**Problem**: Thresholds are not triggering problem states correctly.

**Solutions**:
1. Verify that threshold values are set appropriately for your plants
2. Check that sensor values are within expected ranges
3. Ensure that the "problem" attribute of the plant entity is being monitored
4. Test threshold changes by manually adjusting sensor values
5. Check that time-based conditions (if any) are not preventing threshold evaluation

## Data and Entity Issues

### Missing Entities
**Problem**: Expected plant entities are not appearing in Home Assistant.

**Solutions**:
1. Check that the plant was created successfully in the device list
2. Verify that the integration is loaded and functioning
3. Restart Home Assistant to trigger entity discovery
4. Check the "Entities" section in Home Assistant for any entities in "Removed" or "Disabled" states
5. Look in Home Assistant logs for entity creation errors

### Stale or Incorrect Data
**Problem**: Plant entities show stale or incorrect data.

**Solutions**:
1. Check that underlying sensors are updating correctly
2. Verify network connectivity to all devices
3. Restart the integration by disabling and re-enabling it in Home Assistant
4. Check that the recorder component is functioning properly
5. Examine Home Assistant logs for data processing errors

### DLI Calculation Problems
**Problem**: Daily Light Integral (DLI) values seem incorrect or are not updating.

**Solutions**:
1. Verify that an illuminance sensor is properly assigned to the plant
2. Check that the illuminance sensor is updating regularly
3. Ensure that the illuminance sensor provides sufficient data points for calculation
4. Check that the recorder database is functioning and storing historical data
5. Review logs for DLI calculation errors

## Performance Issues

### Slow Integration Performance
**Problem**: The integration is causing Home Assistant to run slowly.

**Solutions**:
1. Check if you have an excessive number of plants or sensors
2. Verify that the recorder database is not excessively large
3. Consider limiting the history retention period for plant sensors
4. Check system resources (CPU, memory, disk I/O) on your Home Assistant host
5. Review logs for any repeated errors or warnings that might indicate performance issues

### Database Growth
**Problem**: The Home Assistant database is growing rapidly.

**Solutions**:
1. Implement recorder configuration to exclude verbose plant entities if needed
2. Consider setting up database maintenance routines
3. Review which entities are being recorded and exclude non-essential ones
4. Check if sensors are updating too frequently and causing excessive data points
5. Consider using a separate database for plant data if the main database becomes too large

## Tent and Cycle Issues

### Tent Assignment Problems
**Problem**: Unable to assign plants to tents or tent changes are not reflected.

**Solutions**:
1. Verify that the tent exists and is properly configured
2. Check that the tent entity is available and not in an error state
3. Try reassigning the plant to the tent through the plant configuration
4. Check that the tent service is functioning properly
5. Review logs for tent-related errors

### Cycle Management Issues
**Problem**: Problems with creating, assigning, or removing plants from cycles.

**Solutions**:
1. Verify that the cycle exists and is properly configured
2. Check that the cycle entity is available and not in an error state
3. Try reassigning the plant to the cycle through the plant configuration
4. Check that the cycle service is functioning properly
5. Review logs for cycle-related errors

## Service Issues

### Service Call Failures
**Problem**: Plant services (add_watering, replace_sensor, etc.) are failing.

**Solutions**:
1. Verify that you're using the correct service names and parameters
2. Check that the target entities exist and are available
3. Review Home Assistant logs for service call errors
4. Try calling the service through the Developer Tools section first
5. Ensure that the integration is properly loaded and functioning

### Export/Import Problems
**Problem**: Unable to export or import plant configurations.

**Solutions**:
1. Verify that the specified file paths are accessible and have proper permissions
2. Check that there is sufficient disk space available
3. Ensure that the ZIP file format is supported
4. Try using different file paths or directories
5. Check logs for file I/O errors

## Network and Connectivity Issues

### Sensor Connectivity Problems
**Problem**: Sensors become unavailable or show intermittent connectivity.

**Solutions**:
1. Check network connectivity to sensor devices
2. Verify that sensor batteries (if applicable) are sufficiently charged
3. Check for interference or signal strength issues with wireless sensors
4. Restart sensor devices if possible
5. Review network infrastructure for bottlenecks or issues

### Integration Communication Errors
**Problem**: The integration shows communication errors with sensors or services.

**Solutions**:
1. Verify that all required Home Assistant components are loaded and functioning
2. Check network connectivity between Home Assistant and sensor devices
3. Review Home Assistant logs for communication error details
4. Restart Home Assistant to reestablish connections
5. Check that firewall or security software is not blocking communication

## Diagnostic and Logging

### Using Diagnostics
**Problem**: Need to troubleshoot integration issues using diagnostic information.

**Solutions**:
1. Download diagnostic information from the device configuration page
2. Review the diagnostic data for error messages or misconfigurations
3. Check that all required data is present in the diagnostic output
4. Share diagnostic information (after removing sensitive data) when seeking help
5. Use the diagnostic data to verify that entities and sensors are properly linked

### Interpreting Logs
**Problem**: Difficulty understanding error messages in Home Assistant logs.

**Solutions**:
1. Filter logs to show only messages from the "plant" integration
2. Look for ERROR and WARNING level messages
3. Check timestamps to correlate errors with user actions
4. Search for specific error codes or messages online
5. Save relevant log sections when seeking help

## Common Error Messages

### "Entity not found"
**Cause**: Referenced entity doesn't exist or is unavailable.
**Solution**: Verify entity ID and check that the entity exists and is available.

### "Service not found"
**Cause**: Attempting to call a service that doesn't exist or isn't loaded.
**Solution**: Verify service name and check that the integration is properly loaded.

### "Value out of range"
**Cause**: Provided value exceeds acceptable limits for a parameter.
**Solution**: Check parameter limits and provide an appropriate value.

### "Permission denied"
**Cause**: Insufficient permissions to perform an action.
**Solution**: Check user permissions and ensure adequate access rights.

### "Timeout error"
**Cause**: Operation took too long to complete.
**Solution**: Check network connectivity and system performance.

## Advanced Troubleshooting

### Debug Logging
Enable debug logging for more detailed information:

```yaml
logger:
  logs:
    custom_components.plant: debug
```

Add this to your `configuration.yaml` file and restart Home Assistant.

### Database Maintenance
If the database is causing performance issues:

1. Consider purging old data with the `recorder.purge` service
2. Check database integrity with appropriate database tools
3. Consider moving to a more robust database backend if using SQLite

### Integration Isolation
To test if issues are specific to this integration:

1. Disable other custom integrations temporarily
2. Test plant functionality in isolation
3. Re-enable integrations one by one to identify conflicts

## Getting Help

If you're unable to resolve an issue:

1. Check the GitHub issues page for similar problems
2. Provide detailed information when seeking help:
   - Home Assistant version
   - Integration version
   - Error messages from logs
   - Steps to reproduce the issue
   - Diagnostic information (with sensitive data removed)
3. Try reproducing the issue in a test environment if possible
4. Consider creating a minimal test case to isolate the problem

Remember to always backup your Home Assistant configuration before making significant changes or updates.