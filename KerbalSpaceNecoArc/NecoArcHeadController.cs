using System.Collections.Generic;
using UnityEngine;

namespace KerbalSpaceNecoArc
{
    // Builds and maintains the Neco Arc head for a single kerbal (IVA or EVA).
    // Every frame it enforces the desired state from NecoArcConfig's per-kerbal
    // registry so the head can be toggled at runtime:
    //   enabled  -> stock head/face meshes hidden, Neco Arc head shown
    //   disabled -> stock meshes restored, Neco Arc head hidden
    // Restoring the stock meshes is what lets a unique head (e.g. Jeb's) show
    // normally instead of rendering together with the Neco Arc head.
    public class NecoArcHeadController : MonoBehaviour
    {
        public string kerbalName;

        // Only IVA kerbals can enter the first-person view where the game hides
        // the stock head; EVA kerbals never do, so the added head must stay
        // visible there (the stock head renderer is disabled under the helmet).
        public bool hideInFirstPerson = false;

        private Transform bone;
        private GameObject headObject;
        private SkinnedMeshRenderer headRenderer;
        private Mesh nullMesh;
        private readonly Dictionary<string, Mesh> originalMeshes = new Dictionary<string, Mesh>();
        private bool built;

        // The stock kerbal head meshes (used to pick the render layer and to
        // detect the IVA first-person view, where the game hides the head).
        public static bool IsStockHeadMesh(string name)
        {
            switch (name)
            {
                case "headMesh01":
                case "mesh_female_kerbalAstronaut01_kerbalGirl_mesh_polySurface51":
                case "headMesh":
                    return true;
                default:
                    return false;
            }
        }

        // Stock kerbal head/face meshes that must be hidden while the Neco Arc
        // head is active so only one head is visible.
        public static bool IsHiddenKerbalMesh(string name)
        {
            switch (name)
            {
                case "headMesh01":
                case "mesh_female_kerbalAstronaut01_kerbalGirl_mesh_polySurface51":
                case "headMesh":

                case "eyeballLeft":
                case "eyeballRight":
                case "pupilLeft":
                case "pupilRight":
                case "mesh_female_kerbalAstronaut01_kerbalGirl_mesh_eyeballLeft":
                case "mesh_female_kerbalAstronaut01_kerbalGirl_mesh_eyeballRight":
                case "mesh_female_kerbalAstronaut01_kerbalGirl_mesh_pupilLeft":
                case "mesh_female_kerbalAstronaut01_kerbalGirl_mesh_pupilRight":

                case "mesh_female_kerbalAstronaut01_kerbalGirl_mesh_pCube1": // ponytail
                case "ponytail":
                case "tongue":
                case "upTeeth01":
                case "upTeeth02":
                case "mesh_female_kerbalAstronaut01_kerbalGirl_mesh_upTeeth01":
                case "mesh_female_kerbalAstronaut01_kerbalGirl_mesh_downTeeth01":
                case "downTeeth01":
                    return true;
                default:
                    return false;
            }
        }

        public void Start()
        {
            nullMesh = new Mesh();
            Build();
        }

        private void Build()
        {
            var config = NecoArcConfig.instance;
            if (config == null || !config.IsLoaded) return;

            foreach (var t in GetComponentsInChildren<Transform>(true))
            {
                if (t.name == "bn_upperJaw01")
                {
                    bone = t;
                    break;
                }
            }
            System.Diagnostics.Debug.Assert(bone != null, "cannot find bn_upperJaw01");
            if (bone == null) return;

            int layer = bone.gameObject.layer;
            foreach (var smr in GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (IsStockHeadMesh(smr.name))
                {
                    layer = smr.gameObject.layer;
                    break;
                }
            }

            headObject = new GameObject("necoArcHead");
            headRenderer = headObject.AddComponent<SkinnedMeshRenderer>();
            headRenderer.sharedMesh = config.HeadMesh;
            headRenderer.material = config.HeadMaterial;
            headRenderer.bones = new Transform[] { bone };
            headObject.transform.parent = transform;
            headObject.layer = layer;

            built = true;
        }

        public void LateUpdate()
        {
            if (!built || headRenderer == null) return;

            bool enabled = NecoArcConfig.IsEnabledFor(kerbalName);
            Renderer stockHead = null;

            // Re-scan by name every frame rather than caching renderer
            // references: on EVA the game can recreate the head renderer, which
            // would leave a cached reference stale.
            foreach (var smr in GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                if (smr == headRenderer) continue;

                string n = smr.name;
                if (!IsHiddenKerbalMesh(n)) continue;

                if (IsStockHeadMesh(n)) stockHead = smr;

                // Remember the real mesh the first time we see it so we can put
                // it back when the head is toggled off.
                if (smr.sharedMesh != null && smr.sharedMesh != nullMesh
                    && !originalMeshes.ContainsKey(n))
                {
                    originalMeshes[n] = smr.sharedMesh;
                }

                Mesh target;
                if (enabled)
                {
                    target = nullMesh;
                }
                else
                {
                    Mesh original;
                    target = originalMeshes.TryGetValue(n, out original) ? original : smr.sharedMesh;
                }
                if (smr.sharedMesh != target) smr.sharedMesh = target;
            }

            // Hide the Neco Arc head when disabled, or (IVA only) when the stock
            // head is hidden by the game for the first-person view.
            bool firstPersonHidden = hideInFirstPerson && stockHead != null && !stockHead.enabled;
            headRenderer.enabled = enabled && !firstPersonHidden;
        }
    }
}
