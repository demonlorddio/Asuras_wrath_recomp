# D2 tasklist — native lv2 surface (from T-003)

Derived from `re/imports.txt` (480 undefined symbols, each exactly once)
after `ld.lld -r` over the 225 cached PPU objects.

| group | symbols | meaning |
|---|---|---|
| lv2 syscalls | 52 | must be implemented by the native layer |
| unresolved PPU vaddrs | 417 | referenced by compiled code, defined by no object |
| runtime intrinsics | 9 | provided by the rpcs3 runtime, not game code |
| syscall trampoline | 2 | the `sc` path itself |

The syscall numbers found in the EBOOT (`re/ppuanalyser/syscalls.csv`, 66 distinct)
are the *other* half of this surface: numbers here, names in the objects. Match
them via rpcs3's syscall table when the numbers are needed.

## Syscall namespaces

### Event queues / ports (`sys_event_*`) — 9 symbol(s)

- `sys_event_port_connect_local`
- `sys_event_port_create`
- `sys_event_port_destroy`
- `sys_event_port_disconnect`
- `sys_event_port_send`
- `sys_event_queue_create`
- `sys_event_queue_destroy`
- `sys_event_queue_drain`
- `sys_event_queue_receive`

### SPU management (`sys_spu_*`) — 9 symbol(s)

- `sys_spu_image_open`
- `sys_spu_image_open_by_fd`
- `sys_spu_initialize`
- `sys_spu_thread_disconnect_event`
- `sys_spu_thread_group_destroy`
- `sys_spu_thread_group_terminate`
- `sys_spu_thread_read_ls`
- `sys_spu_thread_write_ls`
- `sys_spu_thread_write_spu_mb`

### PPU services (`sys_ppu_*`) — 6 symbol(s)

- `sys_ppu_thread_detach`
- `sys_ppu_thread_get_priority`
- `sys_ppu_thread_get_stack_information`
- `sys_ppu_thread_join`
- `sys_ppu_thread_set_priority`
- `sys_ppu_thread_yield`

### Mutexes (`sys_mutex_*`) — 5 symbol(s)

- `sys_mutex_create`
- `sys_mutex_destroy`
- `sys_mutex_lock`
- `sys_mutex_trylock`
- `sys_mutex_unlock`

### Condition variables (`sys_cond_*`) — 4 symbol(s)

- `sys_cond_create`
- `sys_cond_destroy`
- `sys_cond_signal_all`
- `sys_cond_wait`

### Semaphores (`sys_semaphore_*`) — 4 symbol(s)

- `sys_semaphore_create`
- `sys_semaphore_destroy`
- `sys_semaphore_post`
- `sys_semaphore_wait`

### Filesystem (`sys_fs_*`) — 3 symbol(s)

- `sys_fs_read`
- `sys_fs_stat`
- `sys_fs_write`

### Memory (`sys_memory_*`) — 3 symbol(s)

- `sys_memory_allocate`
- `sys_memory_free`
- `sys_memory_get_user_memory_size`

### Time (`sys_time_*`) — 3 symbol(s)

- `sys_time_get_current_time`
- `sys_time_get_timebase_frequency`
- `sys_time_get_timezone`

### Timers (`sys_timer_*`) — 2 symbol(s)

- `sys_timer_sleep`
- `sys_timer_usleep`

### Console I/O (`sys_tty_*` / `sys_io_*`) — 2 symbol(s)

- `sys_tty_read`
- `sys_tty_write`

### Memory mapping (`sys_mmapper_*`) — 1 symbol(s)

- `sys_mmapper_free_address`

### Reader/writer locks (`sys_rwlock_*`) — 1 symbol(s)

- `sys_rwlock_create`

## Unresolved PPU addresses — 417

These are named after the PPU vaddr they refer to (`__0x…`) but no object
defines them. Either the function was not recompiled (data/unsupported)
or the reference crosses an object boundary the recompiler did not emit.
They are the concrete D1 blocker: the native link cannot close without them.

<details><summary>full list</summary>

- `__0x220c8`
- `__0x33504`
- `__0x34374`
- `__0x3438c`
- `__0x4e968`
- `__0x64224`
- `__0x649e8`
- `__0x86430`
- `__0x898ec`
- `__0x9e250`
- `__0xaec24`
- `__0xb5294`
- `__0xb997c`
- `__0xdfd94`
- `__0xf6228`
- `__0x10385c`
- `__0x1197ec`
- `__0x119a0c`
- `__0x11b30c`
- `__0x11b314`
- `__0x11b930`
- `__0x11b938`
- `__0x11da9c`
- `__0x11ee10`
- `__0x1232a0`
- `__0x133bc4`
- `__0x134a74`
- `__0x13b2c0`
- `__0x13e63c`
- `__0x1403b8`
- `__0x14e284`
- `__0x15ab10`
- `__0x15f884`
- `__0x165a00`
- `__0x16732c`
- `__0x167340`
- `__0x1696a8`
- `__0x1709ec`
- `__0x1864c0`
- `__0x18fe94`
- `__0x1ba61c`
- `__0x1c40c0`
- `__0x1c50ec`
- `__0x1c53b8`
- `__0x1c61c0`
- `__0x1c7400`
- `__0x1c740c`
- `__0x1c7b60`
- `__0x1fb080`
- `__0x1fbe1c`
- `__0x203750`
- `__0x2148f8`
- `__0x214904`
- `__0x2519c4`
- `__0x2526b8`
- `__0x2534c8`
- `__0x25ce60`
- `__0x26f124`
- `__0x2780b4`
- `__0x27b4d0`
- `__0x281dfc`
- `__0x285c2c`
- `__0x2990fc`
- `__0x29d4cc`
- `__0x2a3fc4`
- `__0x2abad4`
- `__0x2ad1f0`
- `__0x2ad1fc`
- `__0x2bc258`
- `__0x2cac64`
- `__0x2cf91c`
- `__0x2d18a4`
- `__0x2d3e88`
- `__0x2df7a0`
- `__0x2e0d58`
- `__0x2e4a44`
- `__0x2e68f8`
- `__0x2f2240`
- `__0x2f4548`
- `__0x2f563c`
- `__0x2f78ac`
- `__0x2f9d90`
- `__0x316af8`
- `__0x31772c`
- `__0x317f08`
- `__0x317f10`
- `__0x319be0`
- `__0x33f210`
- `__0x3439c8`
- `__0x364c80`
- `__0x3749b8`
- `__0x375a6c`
- `__0x393e14`
- `__0x394534`
- `__0x3aac1c`
- `__0x3ab494`
- `__0x3b10f4`
- `__0x3b72fc`
- `__0x3b7328`
- `__0x3b7334`
- `__0x3b74e4`
- `__0x3b7530`
- `__0x3b75d4`
- `__0x3c2c88`
- `__0x3cb478`
- `__0x3d67b8`
- `__0x3d67d8`
- `__0x3d9a14`
- `__0x3dba20`
- `__0x3dc1f8`
- `__0x3dc398`
- `__0x3dd01c`
- `__0x3df500`
- `__0x3e1794`
- `__0x3e1f88`
- `__0x3e3800`
- `__0x3e73e4`
- `__0x3e7bd0`
- `__0x3eaa74`
- `__0x3ef3ac`
- `__0x3f6754`
- `__0x3f822c`
- `__0x3f862c`
- `__0x403630`
- `__0x409308`
- `__0x409988`
- `__0x40a0ec`
- `__0x40df78`
- `__0x416a98`
- `__0x416aa4`
- `__0x41b5a0`
- `__0x41be68`
- `__0x41c7e8`
- `__0x4218c0`
- `__0x4218d0`
- `__0x421ec0`
- `__0x423f60`
- `__0x425fd8`
- `__0x4285e8`
- `__0x4295ac`
- `__0x42ae10`
- `__0x42d7d8`
- `__0x4303ec`
- `__0x433ef8`
- `__0x4397b8`
- `__0x441cb4`
- `__0x4441d0`
- `__0x445000`
- `__0x44dfac`
- `__0x45070c`
- `__0x451d14`
- `__0x455b70`
- `__0x455e4c`
- `__0x455e5c`
- `__0x455e68`
- `__0x456e6c`
- `__0x456e7c`
- `__0x458b24`
- `__0x45a3ec`
- `__0x45a524`
- `__0x45a538`
- `__0x45b788`
- `__0x45bab8`
- `__0x45eff0`
- `__0x46115c`
- `__0x463998`
- `__0x4666c4`
- `__0x4689e4`
- `__0x469e30`
- `__0x46ee04`
- `__0x475558`
- `__0x479ec4`
- `__0x479ff8`
- `__0x47b498`
- `__0x47bc2c`
- `__0x47e210`
- `__0x4820a4`
- `__0x49158c`
- `__0x4b512c`
- `__0x50302c`
- `__0x50f8a4`
- `__0x513978`
- `__0x51c87c`
- `__0x5211ec`
- `__0x521a0c`
- `__0x521a1c`
- `__0x521a24`
- `__0x52303c`
- `__0x540ddc`
- `__0x54b488`
- `__0x556ca0`
- `__0x557f7c`
- `__0x55a48c`
- `__0x566c20`
- `__0x566ebc`
- `__0x569844`
- `__0x578834`
- `__0x57a474`
- `__0x589d08`
- `__0x5a84b4`
- `__0x5b00c8`
- `__0x5b0bb4`
- `__0x5b3428`
- `__0x5b6ef4`
- `__0x5c14b0`
- `__0x5c5f28`
- `__0x5cc844`
- `__0x5d2de8`
- `__0x5e2004`
- `__0x5e2650`
- `__0x5e2eec`
- `__0x5efa5c`
- `__0x5fa3b8`
- `__0x609b98`
- `__0x60a9ec`
- `__0x60ae28`
- `__0x60bd68`
- `__0x60f844`
- `__0x61f464`
- `__0x62213c`
- `__0x64675c`
- `__0x64ac80`
- `__0x653f48`
- `__0x65bab4`
- `__0x661d9c`
- `__0x663198`
- `__0x664c0c`
- `__0x667898`
- `__0x6745fc`
- `__0x674900`
- `__0x6762d4`
- `__0x676890`
- `__0x6791d4`
- `__0x6791e0`
- `__0x67d5b4`
- `__0x67f504`
- `__0x681390`
- `__0x6881c8`
- `__0x68bf40`
- `__0x68c684`
- `__0x690198`
- `__0x69f69c`
- `__0x6a5a9c`
- `__0x6adccc`
- `__0x6b0a14`
- `__0x6c60e8`
- `__0x6c863c`
- `__0x6c86f0`
- `__0x6c8aec`
- `__0x6d818c`
- `__0x6d8198`
- `__0x6d81a0`
- `__0x6d9778`
- `__0x6dbcc4`
- `__0x70716c`
- `__0x7083fc`
- `__0x70df18`
- `__0x712edc`
- `__0x7155a4`
- `__0x71dc60`
- `__0x72e5ac`
- `__0x747fc4`
- `__0x74acfc`
- `__0x752800`
- `__0x7558fc`
- `__0x760bc0`
- `__0x760bc8`
- `__0x761324`
- `__0x7613ec`
- `__0x761748`
- `__0x762600`
- `__0x7653d4`
- `__0x768b08`
- `__0x76b430`
- `__0x76bb2c`
- `__0x77d9e8`
- `__0x77d9f0`
- `__0x782d8c`
- `__0x782d9c`
- `__0x782da8`
- `__0x784bcc`
- `__0x78dda0`
- `__0x78e068`
- `__0x78e08c`
- `__0x78e0a8`
- `__0x78e0b4`
- `__0x78e0d8`
- `__0x78e0f8`
- `__0x791088`
- `__0x796674`
- `__0x797944`
- `__0x798b60`
- `__0x7a3c48`
- `__0x7a3c50`
- `__0x7d8394`
- `__0x7dbb08`
- `__0x7dc05c`
- `__0x7de51c`
- `__0x7dec3c`
- `__0x7e84c8`
- `__0x7e9c04`
- `__0x7e9fc4`
- `__0x7fbf5c`
- `__0x7ff2c8`
- `__0x7ff97c`
- `__0x8066d4`
- `__0x836a28`
- `__0x837c1c`
- `__0x83f158`
- `__0x8485e0`
- `__0x84b4f0`
- `__0x85dcf0`
- `__0x8720ac`
- `__0x872134`
- `__0x873d6c`
- `__0x87b840`
- `__0x87c304`
- `__0x89ad0c`
- `__0x89d5a4`
- `__0x8acc88`
- `__0x8b0374`
- `__0x8b2c04`
- `__0x8b9b84`
- `__0x8c3600`
- `__0x8c3b0c`
- `__0x8c3f08`
- `__0x8c4c0c`
- `__0x8e9f4c`
- `__0x8eb688`
- `__0x8f5ef4`
- `__0x907a68`
- `__0x917e6c`
- `__0x919a10`
- `__0x919a18`
- `__0x91db08`
- `__0x91db10`
- `__0x925fe8`
- `__0x93040c`
- `__0x930d98`
- `__0x935848`
- `__0x936c40`
- `__0x936c4c`
- `__0x93b9cc`
- `__0x93c1c0`
- `__0x959acc`
- `__0x95ba2c`
- `__0x9a5274`
- `__0xf865d0`
- `__0xf8b6e8`
- `__0xf8becc`
- `__0xf8c818`
- `__0xf8cffc`
- `__0xf8dadc`
- `__0xf8e42c`
- `__0xf8f050`
- `__0xf8f9e4`
- `__0xf904b8`
- `__0xf90cec`
- `__0xf918a8`
- `__0xf928e8`
- `__0xf92fcc`
- `__0xf93750`
- `__0xf93f2c`
- `__0xf945b0`
- `__0xf95594`
- `__0xf98a90`
- `__0xfc1144`
- `__0xfc21cc`
- `__0xfc86cc`
- `__0xff6480`
- `__0xffbc78`
- `__0xffe95c`
- `__0x1003280`
- `__0x100329c`
- `__0x10032a8`
- `__0x1008488`
- `__0x1035cbc`
- `__0x1035f48`
- `__0x103d7a0`
- `__0x103d7b0`
- `__0x1041134`
- `__0x104f01c`
- `__0x10505e0`
- `__0x10505e8`
- `__0x106b418`
- `__0x106b6e0`
- `__0x1090758`
- `__0x109dcb0`
- `__0x10dfea0`
- `__0x10e053c`
- `__0x1105c88`
- `__0x11252e0`
- `__0x11252e8`
- `__0x1195e9c`
- `__0x11a5630`
- `__0x11e42a8`
- `__0x11ed340`
- `__0x11f149c`
- `__0x11fa010`
- `__0x11fa128`
- `__0x121ba48`
- `__0x1274c08`
- `__0x1274de4`
- `__0x127ac68`
- `__0x12a57e0`
- `__0x12a7130`
- `__0x12a7138`
- `__0x12a8608`
- `__0x12a8610`
- `__0x12dbef4`
- `__0x12e3214`
- `__0x134f2c0`
- `__0x13d4da8`
- `__0x13f6adc`
- `__0x1406f38`
- `__0x14070f0`
- `__0x14347e0`

</details>

## Runtime intrinsics — 9

Provided by the PPU runtime (atomics, timebase, MMIO, trap), not by D2 game code.

- `__check`
- `__get_tb`
- `__ldarx`
- `__lwarx`
- `__read_maybe_mmio32`
- `__stdcx`
- `__stwcx`
- `__trap`
- `__write_maybe_mmio32`

## Syscall trampoline

- `__syscall`
- `syscall_988`
