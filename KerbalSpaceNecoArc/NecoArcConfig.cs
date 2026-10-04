using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace KerbalSpaceNecoArc
{
    // Holds the single Neco Arc head mesh and its material. The head is a
    // self-contained mesh (head + hair + ears + eyes) baked with its own
    // texture, so there is nothing to configure per kerbal: every kerbal gets
    // the same head.
    public class NecoArcConfig
    {
        public static NecoArcConfig instance = null;

        public Mesh HeadMesh { get; private set; }
        public Material HeadMaterial { get; private set; }

        public bool IsLoaded { get { return HeadMesh != null && HeadMaterial != null; } }

        private readonly Dictionary<string, Texture2D> textures = new Dictionary<string, Texture2D>();
        private Matrix4x4 bindpose;

        // Bounding-box centre of the stock kerbal head mesh, in the same bind-pose
        // space the Neco Arc head is skinned into. The Neco Arc head is shifted so
        // its centre lands here, which makes it overlay the original head.
        private Vector3 stockHeadCenter;

        // Manual fine-tune applied AFTER auto-alignment. Nudge this (then rebuild
        // the plugin) if the head still needs to move: +y up, +z forward, +x
        // right, in KSP mesh units (same scale as the converter's TARGET_HEIGHT,
        // ~0.35 per head). Leave at zero to sit exactly on the stock head.
        public static readonly Vector3 MANUAL_OFFSET = new Vector3(0f, -0.03f, 0f);

        // Per-kerbal on/off state for the Neco Arc head, keyed by kerbal name.
        // A kerbal is enabled (gets the head) unless it is listed here. This is
        // session state so the head can be toggled at runtime without reloading
        // (e.g. to restore a unique stock head like Jeb's and avoid a
        // two-headed model). It is intentionally not persisted to the save.
        private static readonly HashSet<string> disabledKerbals = new HashSet<string>();

        public static bool IsEnabledFor(string kerbalName)
        {
            if (string.IsNullOrEmpty(kerbalName)) return true;
            return !disabledKerbals.Contains(kerbalName);
        }

        public static void SetEnabledFor(string kerbalName, bool enabled)
        {
            if (string.IsNullOrEmpty(kerbalName)) return;
            if (enabled) disabledKerbals.Remove(kerbalName);
            else disabledKerbals.Add(kerbalName);
        }

        public static void ToggleFor(string kerbalName)
        {
            if (string.IsNullOrEmpty(kerbalName)) return;
            SetEnabledFor(kerbalName, !IsEnabledFor(kerbalName));
        }

        private const string DIR = "KerbalSpaceNecoArc/";
        private const string TEX_DIR = DIR + "Textures/";
        private const string MODELS_DIR = "GameData/" + DIR + "Models/";

        public void Load()
        {
            FillTexturesDict();

            CaptureStockHeadRig();
            HeadMesh = LoadMesh("NecoArcHead");
            if (HeadMesh != null)
            {
                AlignToStockHead(HeadMesh);
            }
            HeadMaterial = CreateMaterial(LoadTexture(TEX_DIR + "neco_arc.png"));
        }

        // Finds the stock female kerbal head and records both the bn_upperJaw01
        // bind pose (used to skin the Neco Arc head) and the head mesh's centre
        // (used to position it over the original head).
        private void CaptureStockHeadRig()
        {
            var eva = PartLoader.getPartInfoByName("kerbalEVAfemale").partPrefab.gameObject;
            foreach (SkinnedMeshRenderer smr in eva.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                switch (smr.name)
                {
                    case "headMesh01":
                    case "mesh_female_kerbalAstronaut01_kerbalGirl_mesh_polySurface51":
                    case "headMesh":
                        int i = 0;
                        foreach (var bone in smr.bones)
                        {
                            if (bone.name == "bn_upperJaw01")
                            {
                                bindpose = smr.sharedMesh.bindposes[i];
                                stockHeadCenter = smr.sharedMesh.bounds.center;
                                return;
                            }
                            i++;
                        }
                        break;
                }
            }
            System.Diagnostics.Debug.Assert(false, "CaptureStockHeadRig failed");
        }

        // Shifts the mesh so its bounding-box centre sits on the stock head centre
        // (plus the manual fine-tune). Because the Neco Arc head uses the same
        // bind pose as the stock head, aligning the centres overlays the two.
        private void AlignToStockHead(Mesh mesh)
        {
            Vector3 target = stockHeadCenter + MANUAL_OFFSET;
            Vector3 delta = target - mesh.bounds.center;
            var verts = mesh.vertices;
            for (int i = 0; i < verts.Length; i++)
            {
                verts[i] += delta;
            }
            mesh.vertices = verts;
            mesh.RecalculateBounds();
        }

        private Mesh CreateMesh(
            Vector3[] vertices,
            Vector2[] texcoords,
            Vector3[] normals,
            int[] triangles
        )
        {
            var mesh = new Mesh();
            mesh.vertices = vertices;
            mesh.uv = texcoords;
            BoneWeight[] weights = new BoneWeight[mesh.vertices.Length];
            for (int i = 0; i < weights.Length; i++)
            {
                weights[i].boneIndex0 = 0;
                weights[i].weight0 = 1;
            }
            mesh.boneWeights = weights;
            mesh.bindposes = new Matrix4x4[] { bindpose };
            mesh.triangles = triangles;
            if (normals is null)
            {
                mesh.RecalculateNormals();
            }
            else
            {
                mesh.normals = normals;
            }

            return mesh;
        }

        private Vector3[] LoadVector3Array(string path)
        {
            using (FileStream fs = File.OpenRead(path))
            using (BinaryReader r = new BinaryReader(fs))
            {
                var a = new Vector3[r.ReadUInt32()];
                for (int i = 0; i < a.Length; i++)
                {
                    a[i].x = r.ReadSingle();
                    a[i].y = r.ReadSingle();
                    a[i].z = r.ReadSingle();
                }
                return a;
            }
        }

        private Vector3[] LoadVector3ArrayIfExists(string path)
        {
            if (File.Exists(path))
            {
                return LoadVector3Array(path);
            }
            else
            {
                return null;
            }
        }

        private Vector2[] LoadVector2Array(string path)
        {
            using (FileStream fs = File.OpenRead(path))
            using (BinaryReader r = new BinaryReader(fs))
            {
                var a = new Vector2[r.ReadUInt32()];
                for (int i = 0; i < a.Length; i++)
                {
                    a[i].x = r.ReadSingle();
                    a[i].y = r.ReadSingle();
                }
                return a;
            }
        }

        private int[] LoadIntArray(string path)
        {
            using (FileStream fs = File.OpenRead(path))
            using (BinaryReader r = new BinaryReader(fs))
            {
                var a = new int[r.ReadUInt32()];
                for (int i = 0; i < a.Length; i++)
                {
                    a[i] = r.ReadInt32();
                }
                return a;
            }
        }

        private Mesh LoadMesh(string name)
        {
            string basepath = MODELS_DIR + name;
            if (!File.Exists(basepath + ".vtx") || !File.Exists(basepath + ".idx"))
            {
                return null;
            }
            return CreateMesh(
                LoadVector3Array(basepath + ".vtx"),
                LoadVector2Array(basepath + ".tex"),
                LoadVector3ArrayIfExists(basepath + ".nml"),
                LoadIntArray(basepath + ".idx")
            );
        }

        private Texture2D LoadTexture(string path)
        {
            path = path.Substring(0, path.LastIndexOf('.'));
            Texture2D tex = null;
            textures.TryGetValue(path, out tex);
            return tex;
        }

        private void FillTexturesDict()
        {
            foreach (var tex in Resources.FindObjectsOfTypeAll<Texture2D>())
            {
                textures[tex.name] = tex;
            }
        }

        private Material CreateMaterial(Texture2D texture)
        {
            var mat = new Material(Shader.Find("Diffuse"));
            mat.mainTexture = texture;
            mat.color = Color.white;
            return mat;
        }
    }
}
