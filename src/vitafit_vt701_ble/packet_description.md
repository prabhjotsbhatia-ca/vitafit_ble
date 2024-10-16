
## Packet Structure

```
5A 0A 00 10 XX 00 00 21 YY YY ZZ AA
```

Where:

- `5A`: Start byte
- `0A`: Length byte (10 bytes of payload)
- `00 10`: Fixed bytes (possibly a command or message type)
- `XX`: Status byte
- `00 00`: Fixed bytes (possibly reserved for future use)
- `21`: Fixed byte (possibly a scale identifier or model number)
- `YY YY`: Weight data (2 bytes, big-endian)
- `ZZ`: Checksum or additional data
- `AA`: End byte

## Status Byte (XX)

The status byte (5th byte) seems to indicate the current state of the measurement:

- `00`: Zero or tare weight
- `01`: Unstable weight (still measuring)
- `02`: Stable weight
- `03`: Final weight (after body composition analysis)

## Weight Data (YY YY)

The weight data is stored in bytes 8 and 9 in big-endian format. To get the weight in kilograms, divide the decimal value by 100. For example:

- `22 4C` = 8780 decimal = 87.80 kg

- `24 A9` = 9385 decimal = 93.85 kg

## Body Composition Data

After a stable weight is reached, the scale sends a longer payload for body composition data:

```
5A 0B 00 11 00 00 00 FF FF XX YY ZZ AA
```
Where:
- `0B`: length of packet (11 bytes of payload)
- `XX YY`: Possibly body composition percentages
- `ZZ`: Checksum or additional data
