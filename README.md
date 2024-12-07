# Zone Touch 3 HA Integration

![example](/img/example.png)

A third party Zone Touch 3 Home Assistant Integration. </br>
This project is built off from [@generically-named](https://github.com/generically-named)'s work: [zonetouch3](https://github.com/generically-named/zonetouch3)

This project is very much work in progress. All help appreciated.


## Configuration.yaml
*To enable the integration after adding repository in HACS*

Configuration.yaml Example:
```yaml
fan:
  - platform: zonetouch3
    name: ZoneTouch3 # Optional change
    entities: 8 # Optional change (zone amount)
    port: 7030 # Optional change
    ip_address: 192.168.1.10 # Change
```

## WARNING
There is not yet any safety measure in place to make sure at lease one room is opened before starting your aircon.
Having all rooms toggled off and aircon running may cause damages.
Make sure you have spill zones correctly configured to avoid any concerns. 