# Kerbal Space Neco Arc

A [Kerbal Space Program](https://www.kerbalspaceprogram.com/) mod that replaces
every Kerbal's head with a [Neco Arc](https://typemoon.fandom.com/wiki/Neco-Arc)
catgirl head — in the astronaut complex, in IVA, and on EVA.

It is a pure head replacer: it does not rename your Kerbals or change their
stats. Every Kerbal (stock, Making History, and Breaking Ground variants) gets
the Neco Arc head automatically.

## Toggling the head per Kerbal

Some Kerbals — most notably the "original four" veterans like Jeb, who have
unique stock head models — render their original head *and* the Neco Arc head at
the same time, giving a two-headed look. Rather than removing those heads (some
players still want Jeb's face), you can switch the Neco Arc head off for an
individual Kerbal:

- Send the Kerbal on **EVA**, right-click them, and use the **Hide Neco Arc
  Head** / **Show Neco Arc Head** button in the menu (next to *Remove Helmet*).

Toggling off hides the Neco Arc head and restores that Kerbal's original head,
so there is no longer a double head. The choice is remembered for the rest of
the play session (across IVA/EVA and scene changes) but resets when you restart
the game.

**Tip:** newly hired **female** Kerbals work best and have the fewest visual
issues, since their stock head is the one the mod is fitted to.

## Installation

### CKAN (recommended)

Search for **Kerbal Space Neco Arc** in CKAN and install it.

### Manual

Copy the `GameData/KerbalSpaceNecoArc` folder into your KSP `GameData`
directory. The built plugin (`KerbalSpaceNecoArc.dll`) must be present in
`GameData/KerbalSpaceNecoArc/Plugins/`. Restart KSP afterwards — models and
plugins are only read at load time.

Pre-built release zips (ready to drop into `GameData`) are attached to each
[GitHub release](../../releases).

## Building from source

The plugin references the stock KSP managed assemblies, so point the build at
your KSP install via the `KSPDIR` environment variable (nothing machine-specific
is committed):

```powershell
$env:KSPDIR = 'C:\Program Files (x86)\Steam\steamapps\common\Kerbal Space Program'
dotnet build KerbalSpaceNecoArc\KerbalSpaceNecoArc.csproj -c Release
```

You can also pass it explicitly: `dotnet build -p:KSPRoot="<KSP install>"`.

- **`deploy.ps1`** — regenerate the head model and copy everything (optionally
  `-Dll`) straight into your KSP install for quick iteration.
- **`package.ps1`** — build and produce a clean `dist/KerbalSpaceNecoArc-<version>.zip`
  containing only `GameData/KerbalSpaceNecoArc` (Models, Textures, `.version`,
  and the plugin). Upload that zip as the GitHub release asset CKAN points at.
- **`ModelConverter/`** — the Python pipeline that turns the Neco Arc OBJ into
  the KSP mesh files; see `ModelConverter/viewer/viewer.html` for the live
  offset-tuning preview.

## Credits

- **Based on [Kerbal Space Ponies](https://spacedock.info/mod/352/Kerbal%20Space%20Ponies) by Veon.**
  This mod is a conversion of Kerbal Space Ponies; the head-replacement plumbing
  (IVA/EVA head swapping, model loading, and the OBJ→KSP mesh converter) comes
  from that project. All credit for the original mod goes to its authors.

- **Neco Arc 3D model: ["Neco Arc - Melty Blood:Type Lumina"](https://sketchfab.com/3d-models/neco-arc-melty-bloodtype-lumina-6c08ed209c624c72b150bc282906b63e)
  by [Johan Hoof](https://sketchfab.com/JohanHoof).**
  Licensed under [Creative Commons Attribution 4.0 (CC BY 4.0)](http://creativecommons.org/licenses/by/4.0/).
  The model was decimated and re-fitted to the Kerbal head rig for use in-game.

- **Neco Arc** is a character from *Melty Blood: Type Lumina*, owned by
  Type-Moon / French-Bread. This is an unofficial, non-commercial fan mod and is
  not affiliated with or endorsed by them.

## License

The mod's source code is released under the MIT License (see
[LICENSE.txt](LICENSE.txt)), inherited from Kerbal Space Ponies. The Neco Arc
model is distributed under CC BY 4.0 as noted above.
