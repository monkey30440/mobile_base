# Native compact test traffic

`compact-v4.hex` is the first `compact_payload` byte array from SICK
`unittestMultiscan2LayersCompactV4`, unchanged including its CRC.
Source: [sick_scan_xd 3.9.0](https://github.com/SICKAG/sick_scan_xd/blob/3.9.0/test/src/sick_scansegment_xd/compact_parser_unittests.cpp),
commit `a562c5d098de21f6284359f4dfea97e93bd2b4d5`.
Copyright SICK AG and upstream contributors; see `SICK_LICENSE`.

Loopback replay keeps the native passive receiver alive while testing launch
configuration, parameter services and shutdown. It does not validate picoScan
geometry, device identity, timestamps or physical sensor traffic.

Without input, native listen-only mode skips the initial wait because there is
no connected SOPAS socket, then repeatedly rebuilds services when its FIFO has
fewer than two messages. A no-input fixture is therefore unsuitable for testing
stable parameter-service discovery. The dedicated shutdown regression retains
the original no-input scenario.
