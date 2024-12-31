# Zone Touch 3 HA Integration

![example](/img/example.png)

A third party Zone Touch 3 Home Assistant Integration. </br>
This project is built off from [@generically-named](https://github.com/generically-named)'s work: [zonetouch3](https://github.com/generically-named/zonetouch3)

This project is very much work in progress. All help appreciated.


## Installation

### Via Hacs
The simplest method is to pull the integration via [HACS](https://hacs.xyz/docs/use/)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=GeoDerp&repository=ha_zonetouch3&category=integration)

### Configuration.yaml
After dowloading the integration, to enable the fan entities, append the following into your `/config/Configuration.yaml` file

Configuration.yaml Example:
```yaml
fan:
  - platform: zonetouch3
    name: ZoneTouch3 # Optional change
    entities: 8 # Optional change (zone amount)
    port: 7030 # Optional change
    ip_address: 192.168.1.10 # Change
```

### Reload

Lastly, reload the YAML configuration:  
press `e` key > `>reload all YAML configuration` > Enter  

## WARNING
There is not yet any safety measure in place to make sure at lease one room is opened before starting your aircon.
Having all rooms toggled off and aircon running may cause damages.
Make sure you have spill zones correctly configured to avoid any concerns. 
