# Frostbite container reader for Mass Effect Andromeda — what was built, what was verified

`tools\frostbite\` is a pure-Python 3.14 (standard library only) reader for the
Frostbite container used by Mass Effect Andromeda (MEА), plus a CLI that turns an
asset path into the plot-flag GUIDs the save file actually stores.

Everything below was established by reading the real install at
`C:\Steam\steamapps\common\Mass Effect Andromeda` and is reproducible with the
commands in [§7](#7-commands-to-reproduce). No game file is modified; every read
is a bounded `seek`+`read`.

---

## 1. Headline result

**The requested asset resolves, and its GUIDs are save keys.**

`game/plots/levels/hubs/hub_tempest/plotexpressions/crit_tempest_0725_meridian_returntocity_available`
is an **EBX `PlotLogicExpression`**. It does **not** have a single 16-byte GUID of
its own — in Frostbite an asset is identified by *name*, and the 16-byte GUID
that the save game keys on is the `PlotFlagId.Guid` value stored *inside* the
asset's data. This expression references three such flags, and **all three are
keys in `docs\Career870ee94.plot.json`**:

| flag GUID (.NET text)                  | raw bytes (.NET order)                     | save section | meaning in the expression |
|----------------------------------------|--------------------------------------------|--------------|---------------------------|
| `5fb38cb4-ded5-4470-9193-1aed885201fd` | `b48cb35f d5de 7044 91931aed885201fd`      | `bools`      | required `true`           |
| `fd1b5d9d-e01a-462d-a4ff-9cd48f5b01e0` | `9d5d1bfd 1ae0 2d46 a4ff9cd48f5b01e0`      | `bools`      | required `false`          |
| `771d0593-e901-41f5-ba94-f524783b0378` | `93051d77 01e9 f541 ba94f524783b0378`      | `ints`       | `EqualTo` `50`            |

The partition's own GUID (`ce2e7508-81a4-11e5-bb6a-b63bdec01164`, from the
partition header at offset `0x28`) is **not** a save key — see §5.4. That is an
important negative: "the asset GUID" and "the plot-flag GUID" are different
things, and only the latter appears in the save.

Extending the same lookup over the project's `docs\plot-names.txt` maps
**1,042 of the save's 78,368 flags to asset names** (see §8) — a 1→many join,
because one expression references several flags.

---

## 2. Container layout as it exists on disk

```
Data\layout.toc                     superbundle list + install manifest   (Ooa + DiCE)
Data\initfs_Win32                   install file system (not needed here)
Data\chunkmanifest                  (not needed here)
Data\Win32\*.sb / *.toc             top-level superbundles
Data\Win32\<group>\**\*.sb / *.toc   nested superbundles (game\levels\hubs\tempest\tempest.sb ...)
Data\Win32\streaminginstall\<pkg>\cas.cat + cas_NN.cas     <- the actual data
Patch\...                           same tree, higher priority
Update\<DLC>\Data\...               DLC overlays
```

Measured on this install:

| thing | count |
|---|---|
| `.toc` files | 223 |
| `.sb` files | 221 |
| `cas.cat` files | 35 |
| `.cas` files | 129 (46.3 GB total) |
| `ebx`+`res` records across all `.sb` | 3,092,044 listings |
| unique asset names | 255,641 |
| unique chunk sha1 in catalogs | 605,770 |

Source priority used by the tool (matches the game): **Patch > Update > Data**.
The same asset is usually listed in *many* superbundles with the *same* sha1
(e.g. the target appears in 81 listings across 10 `.sb` files) because the cas is
content-addressed — that is deduplication, not 81 copies.

---

## 3. Formats actually verified (byte-level evidence)

Run `python tools\frostbite\run.py evidence` to print everything in this section
from the live files. The numbers below are that command's output.

### 3.1 File layers: `.toc` = Ooa obfuscation → DiCE signature

`.sb` files have **no** layer (see §3.2). `.toc` and `layout.toc` do, and it is a
**stack of two**:

```
Data\layout.toc  (41555 bytes)
last 36     d1 01 00 00 40 65 21 61 64 6e 58 64 24 5e 21 72 66 4f 73 72 44
            79 49 72 49 21 78 56 67 48 65 41 21 36 56 63
            \_ 01 d1 = 465 _/  \_ "@e!adnXd$^!rfOsrDyIrI!xVgHeA!6Vc" (32 bytes) _/
setupLength 465        (little-endian int32 at fileSize-36)
decrypted   version=4 mode=2 seed=225 plaintextSize=41090
check       plaintextSize 41090 + setupLength 465 == fileSize 41555  [True]
after Ooa   41090 bytes, first 16  00 d1 ce 01 00 00 00 00 98 66 e4 91 ...
            -> 0x01CED100 = DiCE *signature* layer
after DiCE  40534 bytes (8 + 548 byte header skipped), first 16
            82 d2 bc 02 01 73 75 70 65 72 42 75 6e 64 6c 65   = DbObject, "superBundles"
```

* **Ooa** (`@e!adnXd$^!rfOsrDyIrI!xVgHeA!6Vc`): the trailing 36 bytes hold the
  setup-block length and a signature. The setup block is "bogocrypted" — a
  DICE byte-cipher with a table-driven section mixer. Two independent checks
  confirm the port is exact: `version` decrypts to `4` (valid), and
  `plaintextSize + setupLength == fileSize` for **223/223** `.toc` files.
* The body is then XORed with a rolling one-byte key seeded from `setup[5]`
  (mode 2). Mode 3 is stored-plain, mode 1 is unimplemented upstream as well.
* **Gotcha that cost a debugging cycle:** the seed byte `setup[5]` is itself
  modified *at the end* of the bogocrypt routine (`data[5] ^= e`, gated on a
  `uint16` at offset 325 being 1/2/4/8). Omitting that final tweak yields a
  body that is still 99% correct-looking but does not parse.
* **DiCE signature** (`0x01CED100`): `8 + 548` bytes of header, then payload.
  This is *inside* the Ooa layer — a `.toc` is Ooa(DiCE(DbObject)).
* The `0x00CED100` DiCE *obfuscation* variant (different layer) does not occur in
  this install; it is implemented anyway so the reader fails cleanly.

### 3.2 `.sb` = a plain DbObject stream

```
Data\Win32\anchorchannels.sb  (6857 bytes)
first 32    82 c6 35 01 62 75 6e 64 6c 65 73 00 ba 35 82 92 02 07 70 61 74 68 00 ...
decode      82        tag: Object, flags=4
            c6 35     packed varint -> object length 6854
            01        tag: Array
            "bundles" property name (NUL-terminated)
            ba 35     array length varint
            82 92 02  tag: Object, length 274  (one BundleInfo)
            07 "path" tag: String
object end  body starts at 0x3, length 6854, file 6857 -> ends exactly at EOF [True]
```

DbObject encoding (verified against Gibbed's `DbObject/Serializer.cs` **and** the
bytes above):

* one tag byte per value; `tag & 0x1F` = type, `tag >> 5` = flags
* types used here: `1 Array, 2 Object, 6 Bool, 7 String, 8 Int32, 9 Int64,
  12 Float64, 15 Guid, 16 SHA1(20 raw bytes), 19 Bytes`
* containers are prefixed with a **7-bit little-endian varint** covering the
  bytes after the varint; elements are terminated by a tag of type `0`
* strings are varint-length-prefixed and NUL-terminated *inside* the length
* `Guid` fields are 16 bytes with **big-endian** data1/2/3 (Gibbed reads them
  with `ReadValueGuid(Endian.Big)`) — the opposite convention to partition data,
  see §5.4

`.sb` structure: `{ bundles: [ { path, magicSalt, ebx[], dbx[], res[], chunks[],
chunkMeta[], alignMembers, ridSupport, storeCompressedSizes, ... } ] }`, and each
`ebx`/`res` entry is `{ name, sha1, size, originalSize }` (+ `resType`,
`resMeta`, `resRid` for `res`). That `sha1 → cas.cat → cas_NN.cas` chain is the
whole name→data path; it needs no `.toc` at all.

### 3.3 `cas.cat` = DiCE signature → NyanNyan catalog

```
Data\Win32\streaminginstall\ayainstallpackage\cas.cat  (2631040 bytes)
first 16    00 d1 ce 01 00 00 00 00 ...   -> DiCE signature layer
stripped    2630484 bytes (= 2631040 - 556)
first 16    4e 79 61 6e 4e 79 61 6e 4e 79 61 6e 4e 79 61 6e   "NyanNyan" x2
            two little-endian uint64 = 0x6E61794E6E61794E
counts      normal=72,999  patch=0  encrypted=31
entries     start at 0x28, 36 bytes each:
            sha1[20] offset u32 size u32 tailSize u32 dataIndex u8 isEncrypted u8 pad[2]
patches     start after normals: 60 bytes (id, baseId, deltaId)
encrypted   after normals: NormalEntry + { size u32, keyId char[8], unknown[32] }
```

Parsing all 35 catalogs consumes exactly each file's stripped length
(a built-in checksum: `pos == len(data)`), yielding 605,770 unique sha1, 1,921,276
normal / 35,027 patch / 792 encrypted entries.

### 3.4 `.cas` chunk = big-endian block header(s) + zstd

```
cas_02.cas @0x179A (834 bytes)
first 24    00 00 05 60 0f 70 03 3a 28 b5 2f fd 60 60 04 85 ...
block 0     uncompressedSize = 0x00000560 = 1376
            flags            = 0x0F70033A
              type           = flags >> 24      = 0x0F = 15 = zstd
              compressionFlags = (flags >> 20) & 0xF = 7
              compressedSize = flags & 0xFFFFF = 0x33A = 826
decompressed 1376 bytes == originalSize [True]
```

Blocks repeat until `originalSize` bytes are produced (there is no terminator, so
`originalSize` from the `.sb` is mandatory). Compression types seen: `15 zstd`
(MEA profile `EbxCompression: 15`), `0 none` (stored). `2 zlib` is implemented
for completeness.

**zstd needs no third-party code**: Python 3.14 ships `compression.zstd` (PEP
784), which is what the tool uses (`compression.zstd (stdlib, zstd 1.5.7)`).
A `ctypes` fallback against `libzstd.1.3.4.dll` from the FrostyEditor
`ThirdParty` folder exists but was not needed.

**Patch-delta chunks** (`PatchEntry`, 35,027 of them) are implemented too: the
base and delta are raw *compressed block streams*, and the delta interleaves
`uint32 BE` control words (`type = c >> 28`, `count = c & 0x0FFFFFFF`; `0 Copy`,
`1 CompressedChange`, `2 UncompressedChange`, `3 Add`, `4 Remove`). The result is
already decompressed. Without this, 8 of 60 sampled assets failed; with it,
60/60 pass. Example: `game/weapons/mods/shotgun/weaponmod_shotgun_barrel_04c`
is a 26-byte delta that reconstructs a 4416-byte partition.

### 3.5 EBX partition — self-checking header

```
+0x00 magic                ce d1 b2 0f                  0x0FB2D1CE (little-endian)
+0x04 headerSize           50 04 00 00                  1104
+0x08 dataSize             10 01 00 00                  272
+0x0C importCount          00 00 00 00                  0
+0x10 instanceCount        03 00                        3
+0x12 namedInstanceCount   03 00                        3
+0x14 exportedInstanceCount 03 00                       3
+0x16 typeDefinitionCount  0d 00                        13
+0x18 fieldDefinitionCount 19 00                        25
+0x1A nameTableSize        80 01                        384
+0x1C stringTableSize      70 00 00 00                  112
+0x20 arrayCount           02 00 00 00                  2
+0x24 arrayOffset          90 00 00 00                  144
+0x28 guid                 08 75 2e ce a4 81 e5 11 bb 6a b6 3b de c0 11 64
```

The header is **self-checking**, which is why a misparse cannot hide:

```
headerSize == 64 + imports*32 + nameTableSize + fields*16 + types*16
             + align(instances*4, 16) + align(arrays*12, 16)
1104       == 64 + 0 + 384 + 25*16 + 13*16 + 16 + 32          [True]
dataSize + headerSize == chunk length                          [True]
```

After the header: imports (32 B each), name table (NUL-separated UTF-8), field
defs (16 B: `nameHash u32, flags u16, typeIndex u16, dataOffset u32, unknown u32`),
type defs (16 B: `nameHash u32, fieldStart i32, fieldCount u8, alignment u8,
flags u16, dataSize u16, unknown u16`), instances (`typeIndex u16, count u16`,
16-aligned), arrays (`dataOffset u32, itemCount i32, typeIndex i32`, 16-aligned),
then the data blob. Name hashes are **DJB2** (`h = 5381; h = h*33 ^ byte`), and
the name table is the dictionary, so field/type names are recovered exactly.

`DefinitionFlags`: `DataType = (raw >> 4) & 0x1F`, `DataKind = (raw >> 2) & 3`,
`DataFlags = (raw >> 11) & 0x1F`.

Two layout details that matter for correctness:

* the data blob **begins with the string table** (`stringTableSize` bytes) and
  instance offsets are absolute from there;
* only the first `namedInstanceCount` *instance entries* carry a 16-byte instance
  GUID;
* **inheritance** is a field named `$` with `DataType.Void` whose `typeIndex` is
  the base class. Frostbite stores only a type's own fields, so the reader merges
  the base chain. Without this, a `PlotLogicBooleanFlagRule` looks like it has
  only `DesiredValue` and the `Flag` GUID is invisible — this was the second
  real bug found.

For the target asset the decode is:

```
PlotLogicExpression        bc771096b11d2a5f6437e9ec327396b0
  Name = game/plots/levels/hubs/hub_tempest/plotexpressions/crit_tempest_0725_meridian_returntocity_available
  ExpressionRules = [BooleanFlagRule, BooleanFlagRule, IntFlagRule]
  MatchType = 0 (ALL)
PlotLogicBooleanFlagRule  b927fe25600c2e449c099824105b2445
  Flag.PlotFlagId.Guid = 5fb38cb4-ded5-4470-9193-1aed885201fd   DesiredValue = True
PlotLogicBooleanFlagRule  c9e6846047108d44a38717571cc7399c
  Flag.PlotFlagId.Guid = fd1b5d9d-e01a-462d-a4ff-9cd48f5b01e0   DesiredValue = False
PlotLogicIntFlagRule      faba12a3de8c2743885dad44f83312a7
  Flag.PlotFlagId.Guid = 771d0593-e901-41f5-ba94-f524783b0378   Operator = EqualTo, DesiredValue = 50
```

Note the type chain, which is the general shape of MEA plot logic:
`PlotLogicExpression` → `PlotLogicFlagRule` (has `Flag : PlotFlagReference`) →
`PlotFlagReference` (has `PlotFlagId : PlotFlagId`) → `PlotFlagId` (has `Guid`).

---

## 4. Why the GUID is only in the data (corroborating the earlier negative)

For the target's superbundles, the raw GUID bytes appear **zero** times in the
metadata:

```
Patch/Win32/game/levels/hubs/tempest/tempest.sb   9,137,446 bytes  hits: [-1, -1, -1, -1]
Patch/Win32/galaxysystemcontent.sb                5,303,776 bytes  hits: [-1, -1, -1, -1]
Data/Win32/game/levels/hubs/tempest/tempest.sb    9,209,425 bytes  hits: [-1, -1, -1, -1]
   (needles: the three flag GUIDs *and* the partition GUID)
```

So the earlier conclusion stands and is now explained: `.sb`/`.toc` metadata only
carries a *name* and a *sha1*; the 16-byte GUID exists only inside compressed
asset data, which is why the whole chain in §2 is required.

---

## 5. What worked, what did not

### 5.1 Worked

| Claim | Evidence |
|---|---|
| All 223 `.toc` files parse after Ooa+DiCE | `223/223`, plus the setup-size identity |
| All 221 `.sb` files parse as DbObject | `3,092,044` ebx/res listings, every one with a 20-byte sha1 |
| All 35 `cas.cat` parse exactly | `pos == len(data)` per file, 605,770 unique sha1 |
| Chunk decompression is right | 60/60 sampled chunks decompress to exactly `originalSize` |
| The name→data path is right | **57/57** sampled assets embed an `Asset.Name` that equals the path used to fetch them |
| Partitions are parsed correctly | header invariant holds; instances/fields decode into sane typed values |
| Patch deltas | 8/60 sampled assets needed them; all now parse |
| The target's GUIDs are save keys | 3/3 in `docs\Career870ee94.plot.json` |

The strongest check is the `Asset.Name` one: it closes the loop
`name → .sb → sha1 → cas.cat → cas bytes → zstd/patch → partition → data` using
data the format itself vouches for, and it cannot pass by coincidence.

### 5.2 Did not work / not implemented

* **Encrypted chunks (792 catalog entries).** The key id lives in
  `initfs_Win32/Scripts/CasEncrypt.yaml` (a YAML blob inside the install file
  system); the AES/envelope handling was not implemented. The tool reports the
  chunk and key id explicitly instead of guessing. No plot asset encountered hit
  this path.
* **`layout.toc` contents are parsed but barely used.** The reader understands
  `superBundles`/`installManifest`/`fs`/`head` as generic DbObject values, but
  does not model install chunks; the tool finds superbundles by walking the
  filesystem instead. `layout.toc` is therefore *validated*, not *depended on*.
* **No `PlotFlagId` → name table exists in the game.** 255,641 asset names, but
  plot flags are anonymous GUIDs referenced from expressions; only 1,152 assets
  live under `game/plots/`. Consequence: only ~1.3% of the save's 78,368 flags
  can be named this way (§8), and the rest have no name anywhere in the assets.
* **One asset → many flags.** An expression references 2–4 flags on average
  (one outlier has 90), so "the asset's GUID" is not well defined for
  `PlotLogicExpression` assets. The tool prints the *list* and marks which are
  save keys.
* **Partition GUID is not the save key.** `ce2e7508-…` is absent from the save;
  do not use it to join.

---

## 6. GUID byte order (the detail that breaks joins)

* **Save file**: keys are `.NET Guid` text. Raw bytes are
  `data1`/`data2`/`data3` little-endian + `data4` verbatim, i.e.
  `bytes.fromhex(t[0:8])[::-1] + bytes.fromhex(t[9:13])[::-1] + …`.
* **EBX asset data** (`PlotFlagId.Guid`, instance GUIDs, the partition header
  GUID): stored in exactly that `.NET` raw order (Gibbed reads it with
  `ReadValueGuid(Endian.Little)`), so a raw 16-byte match against the save works
  directly. Example: text `5fb38cb4-ded5-4470-9193-1aed885201fd` ↔ bytes
  `b4 8c b3 5f d5 de 70 44 91 93 1a ed 88 52 01 fd`.
* **DbObject `Guid` fields** (`.toc` chunk ids, layout manifests) use
  *big-endian* data1/2/3 instead. Both are normalised through
  `dbobject.Guid`, which renders text the same way.

---

## 7. Commands to reproduce

All commands run from the project root
(`C:\Users\unowi\Documents\APWorldMaker\Mass Effect Andromeda APWorld`).
`--game PATH` overrides the install location; `--roots patch|update|data`
restricts the search; the superbundle index is cached (gzipped, 24 MB) in
`tools\frostbite\_cache\sb-index.pickle.gz` and invalidated automatically by any
`.sb` size/mtime change. Delete it (or pass `--no-cache`) to rebuild, ~30 s.

```powershell
# 0. overview: file counts, catalogs, zstd backend, save dump
python tools\frostbite\run.py info

# 1. list asset names (name, sha1, size) - filter + limit
python tools\frostbite\run.py ls --filter plotexpressions/crit_tempest_0725
python tools\frostbite\run.py ls --filter hub_tempest/plotexpressions --root patch --limit 3 --unique

# 2. locate one asset: superbundle listings + cas file/offset
python tools\frostbite\run.py find game/plots/levels/hubs/hub_tempest/plotexpressions/crit_tempest_0725_meridian_returntocity_available --data

# 3. THE ANSWER: GUID(s) in .NET text form, annotated against the save dump
python tools\frostbite\run.py guid game/plots/levels/hubs/hub_tempest/plotexpressions/crit_tempest_0725_meridian_returntocity_available
python tools\frostbite\run.py guid <name> --json      # machine readable
python tools\frostbite\run.py guid <name> --no-save   # skip save annotation

# 4. raw decompressed bytes
python tools\frostbite\run.py dump <name> --out out\asset.ebx --partition

# 5. self-test (11 checks, ~35 s)
python tools\frostbite\run.py selftest

# 6. print every byte-level fact quoted in this document
python tools\frostbite\run.py evidence

# 7. bulk join: name list -> GUIDs (JSON)
python tools\frostbite\run.py join --names docs\plot-names.txt --out docs\plot-flag-join.json
```

Equivalent module form (no wrapper script): `cd tools; python -m frostbite guid <name>`.

### 7.1 `guid` on the target (actual output)

```
asset        game/plots/levels/hubs/hub_tempest/plotexpressions/crit_tempest_0725_meridian_returntocity_available
listing      Patch/Win32/galaxysystemcontent.sb
bundle       win32/game/space/systems/nexus_09_galaxydataasset_autobundle [ebx]
sha1         ec4d21d620afe122d4489ec4749c2eb06358a108
cas          cas_02.cas @0x179A (834 bytes) -> 1376 bytes [zstd:826->1376]
partition    magic 0x0FB2D1CE, 4 instance(s), 13 type(s), 25 field(s), 2 array(s), 0 import(s)
embedded     Asset.Name = game/plots/levels/hubs/hub_tempest/plotexpressions/crit_tempest_0725_meridian_returntocity_available  [matches requested path]
partition-guid ce2e7508-81a4-11e5-bb6a-b63bdec01164   (header offset 0x28; not a save key)
flag-guid(s)  3 PlotFlagId.Guid value(s):
  5fb38cb4-ded5-4470-9193-1aed885201fd  raw=b48cb35fd5de704491931aed885201fd  [save:bools]  PlotLogicBooleanFlagRule.Flag.PlotFlagId.Guid
  fd1b5d9d-e01a-462d-a4ff-9cd48f5b01e0  raw=9d5d1bfd1ae02d46a4ff9cd48f5b01e0  [save:bools]  PlotLogicBooleanFlagRule.Flag.PlotFlagId.Guid
  771d0593-e901-41f5-ba94-f524783b0378  raw=93051d7701e9f541ba94f524783b0378  [save:ints]  PlotLogicIntFlagRule.Flag.PlotFlagId.Guid
NOTE          this asset references 3 plot flags; it has no single 16-byte GUID of its own (MEA assets are named, not GUID-keyed).  The save-file join is the flag list above.

GUID          5fb38cb4-ded5-4470-9193-1aed885201fd
RAW           b48cb35fd5de704491931aed885201fd
SAVE-JOIN     3/3 flag GUID(s) found in the save dump
```

### 7.2 `find` (actual output, trimmed)

```
asset    game/plots/levels/hubs/hub_tempest/plotexpressions/crit_tempest_0725_meridian_returntocity_available
listings 81 (highest priority first)
 * Patch/Win32/galaxysystemcontent.sb
     bundle=win32/game/space/systems/nexus_09_galaxydataasset_autobundle kind=ebx root=patch
     sha1=ec4d21d620afe122d4489ec4749c2eb06358a108 size=834 originalSize=1376
   ... 78 more listing(s) (same sha1 = cas-level dedup); use --all to show them
   distinct sha1 among listings: 1
chunk     kind=normal
          cas=...\Patch\Win32\streaminginstall\spinitialinstallpackage\cas_02.cas
          offset=0x179A (6042) size=834
          catalog=...\Patch\Win32\streaminginstall\spinitialinstallpackage\cas.cat
          decompressed=1376 bytes, 1 block(s)
```

### 7.3 `ls` (actual output)

```
game/plots/levels/hubs/hub_tempest/plotexpressions/crit_tempest_0725_meridian_returntocity_available	ec4d21d620afe122d4489ec4749c2eb06358a108	834	1376	Patch/Win32/galaxysystemcontent.sb
# 1 name(s) matched; index built from 221 superbundle(s), 255641 unique names [cache hit]
```

### 7.4 `dump` (actual output)

```
asset        game/plots/levels/hubs/hub_tempest/plotexpressions/crit_tempest_0725_meridian_returntocity_available
sha1         ec4d21d620afe122d4489ec4749c2eb06358a108
cas          cas_02.cas @0x179A (834 bytes)
wrote        docs\_tmp_target.ebx (1376 bytes, sha1 adf61475a96c5f520b00cd5592bc24183b8eb1b9)
  magic           0x0FB2D1CE (ce d1 b2 0f)
  partition GUID  ce2e7508-81a4-11e5-bb6a-b63bdec01164
  instances       4 (3 named, 3 exported) ...
```

---

## 8. Self-test (actual output)

```
frostbite self-test against C:\Steam\steamapps\common\Mass Effect Andromeda
roots: patch, update, data

1. table-of-contents files
  PASS  all 223 .toc files parsed  [ooa:223]
  PASS  223/223 Ooa setup blocks self-consistent  [plaintextSize + setupSize == fileSize]
2. superbundles
  PASS  all 221 .sb files parsed  [3,092,044 ebx/res listings]
  PASS  every ebx/res record has a 20-byte sha1
3. cas.cat catalogs
  PASS  35 catalog(s) parsed to exactly their file length  [605,770 unique sha1]
4. sampled EBX chunks: decompress + partition header + embedded name
  PASS  60/60 sampled chunks decompressed and parsed  [76 GUID-typed value(s) decoded]
  PASS  57/57 embedded Asset.Name values equal the asset path they were fetched by
5. documented target asset
  PASS  target resolved  [Patch/Win32/galaxysystemcontent.sb sha1=ec4d21d620afe122d4489ec4749c2eb06358a108]
  PASS  target partition parsed  [partition GUID ce2e7508-81a4-11e5-bb6a-b63bdec01164, 4 instances]
  PASS  3 flag GUIDs match the documented set  [5fb38cb4-…, 771d0593-…, fd1b5d9d-…]
  PASS  3/3 target flag GUIDs are keys in the save dump  [5fb38cb4-… -> bools; fd1b5d9d-… -> bools; 771d0593-… -> ints]

11/11 checks passed in 33.8s
SELFTEST OK
```

`--sample N` changes the number of sampled chunks.

---

## 9. Join result: `docs\plot-names.txt` → flag GUIDs

```powershell
python tools\frostbite\run.py join --names docs\plot-names.txt --out docs\plot-flag-join.json
```

```
names read          1,153
found in a bundle   1,153
partition parsed    1,153
  with flags        1,132
  without flags     21
failed/unreadable   0
distinct flag GUIDs 1,352, 1,042 of them are save keys
```

* `1,152` of the names are *every* asset under `game/plots/` in the whole
  install, so this is effectively the complete plot-asset sweep.
* 21 assets carry no `PlotFlagId` (e.g. `…/mea_main_plotlogic/mea_m3_exaltation_mission_available`,
  the `deprecated_global_squad_*` checks) — they are pure logic, not flag refs.
* Distribution of flags per asset: `0 → 21`, `1 → 100`, `2 → 342`, `3 → 201`,
  `4 → 282`, `5–16 → 191`, `>16 → 16` (largest: one 90-flag aggregate).
* Coverage of the save: **1,042 of 78,368 flag GUIDs (1.3 %)** get a name this
  way. The remaining 77,326 are never referenced by any `game/plots/` asset; to
  reach them one would have to sweep all 255,641 assets (~58 ms each ≈ 4 h
  single-threaded) or target conversation/quest superbundles.

`docs\plot-flag-join.json` contains both directions:

```json
{ "stats": {...},
  "assets": [ { "name": "...", "status": "ok", "sha1": "...",
                "partition_guid": "...",
                "flags": [ {"guid": "...", "path": "PlotLogicBooleanFlagRule.Flag.PlotFlagId.Guid",
                            "save_kinds": ["bools"]} ] } ],
  "guid_to_names": { "<guid>": ["<asset name>", ...] } }
```

---

## 10. Files created

```
tools\frostbite\__init__.py      package metadata
tools\frostbite\dbobject.py      DbObject/DbObjectFile reader (tagged values, varints)
tools\frostbite\filelayer.py     Ooa deobfuscation + DiCE signature/obfuscation layers
tools\frostbite\catalog.py       cas.cat parsing + sha1 index
tools\frostbite\compress.py      Frostbite block decompression (zstd via stdlib, zlib, none)
tools\frostbite\patch.py         PatchEntry delta application (base + delta)
tools\frostbite\partition.py     EBX partition: header, names, types, fields, instances, GUIDs
tools\frostbite\vfs.py           asset index (name -> sha1 -> cas), patch priority, caching
tools\frostbite\cli.py           ls / find / guid / dump / join / info / evidence / selftest
tools\frostbite\selftest.py      the 11 consistency checks in §8
tools\frostbite\run.py           direct launcher (python tools\frostbite\run.py ...)
tools\frostbite\__main__.py      python -m frostbite ...
tools\frostbite\_cache\          superbundle index cache (regenerated on demand)
docs\FROSTBITE-READER.md         this report
docs\plot-flag-join.json         name -> GUID join (generated, 1,153 names)
```

Scratch material (Gibbed/Frosty reference sources used for the port) is under
`tools\scratch\ref\`; it is not needed at runtime.

Nothing outside the project root was written, and no game file was touched.

---

## 11. Cross-check against a third-party EBX document (BF4-era)

A user-supplied reference (`Frostbite3_Editor/__DOCUMENTATION__/ebx/ebx.txt`)
describes the older BF4 EBX header. It agrees with what was measured here on the
points that matter, and disagrees in ways that pin the MEA variant down:

| doc field (after `fb2` magic) | MEA bytes at | MEA value | agrees? |
|---|---|---|---|
| `u32` string-section offset | `+0x04` | 1104 (= headerSize, where string data begins) | yes |
| `u32` string-section length to EOF | `+0x08` | 272 (= dataSize) | yes |
| `u32` external GUID count | `+0x0C` | 0 (= imports) | yes |
| `u16` instance-repeater count | `+0x10` | 3 | yes |
| `u16` repeaters-with-GUID count | `+0x12` | 3 (only these carry instance GUIDs) | yes |
| `u16` unknown | `+0x14` | 3 | **no** — this is `exportedInstanceCount` in MEA (Gibbed's name) |
| `u16` complex count | `+0x16` | 13 (= type definitions) | yes |
| `u16` field count | `+0x18` | 25 | yes |
| `u32` keyword-section size | `+0x1A` | would read `0x00700180` = 7,340,416 | **no** |
| `u32` string-section size | `+0x1E` | would read `0x00020000` | **no** |
| `u32` array-repeater count | `+0x22` | would read `0x00900000` | **no** |
| `u32` payload size | `+0x26` | would read `0x00007508` | **no** |
| `byte[16]` file GUID | `+0x28` | `08 75 2e ce …` | yes (position) |
| `byte[8]` padding | `+0x38` | `00 00 00 00 00 00 00 00` | yes (all zero) |

So the doc's BF4 header is **66** bytes, MEA's is **64**: MEA stores the name
table size as a `u16` and shifts the tail by two bytes, which is why the doc's
`u32 keyword-section size` reads as noise. Everything from `+0x28` on matches
exactly (16-byte GUID, then 8 zero bytes), and the header-size identity in §3.5
proves the MEA reading independently of any document.

Two other doc claims, tested:

* *"Other files may store the magic swapped (`CF B2 D1 0F`)"* — the reader detects
  both byte orders and switches endianness accordingly (all MEA EBX here are
  little-endian).
* *"Field type `0x407d`/`0x409d` are strings with a signed length"* — that is the
  BF4 16-bit type encoding. MEA uses a different scheme: `DefinitionFlags` with
  `DataType = (raw >> 4) & 0x1F`, where `7 = String2` is a `u32` **offset into
  the string table** (no length, `0xFFFFFFFF` = null). This was validated by
  decoding `Asset.Name`, which equals the requested asset path in 57/57 sampled
  assets.
* LZ4 (documented in the same repo) was **not** encountered: across 1,200+
  decompressed chunks only `type 15 = zstd` and `type 0 = none` appear.

### What a non-EBX chunk looks like

`res` entries are resource payloads, not partitions, and the tool says so with
the observed bytes rather than guessing:

```
res  animations/.../5000_dsg_merchants_win32_antstate      zstd 1263 -> 2664
     first 32  00 00 00 01 00 00 00 78 00 00 00 01 00 00 00 01 00 00 00 01 ...
     parses as partition: NO -> bad partition magic 00 00 00 01
res  game/ai/speciespoweroutlaw/asari_bioticshield/fxm_bioticshield_asa_mesh  zstd 330 -> 740
     first 32  97 6b d6 bf 97 6b d6 bf a4 b0 1f bf 00 00 00 00 ...
     parses as partition: NO -> bad partition magic 97 6b d6 bf   (float data: -1.6777, ...)
```

---

## 12. Limitations / next steps

1. **Encrypted chunks** (792 entries) — implement `initfs_Win32` +
   `Scripts/CasEncrypt.yaml` + the AES envelope if any needed asset lands there.
2. **Full flag coverage** — sweep all 255,641 asset names (or only
   conversation/quest/superbundle families) to find the remaining 77,326 flags.
   The reader already resolves any name; only wall-clock time is the obstacle,
   and the cas handle could be cached per process to speed that up.
3. **`layout.toc` modelling** — not required for name→GUID, but would replace the
   filesystem walk with the authoritative install manifest.
4. **Type-driven output** — the partition reader is generic (it decodes any
   struct/enum/list/array), so a `dump --json <name>` of a whole asset's object
   graph is a small addition on top of `Partition.struct`.
