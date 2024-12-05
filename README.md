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
    name: ZoneTouch3 #optional change
    port: 7030 #optional change
    ip_address: 192.168.1.10 #change
```