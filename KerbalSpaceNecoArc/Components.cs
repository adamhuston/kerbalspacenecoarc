using UnityEngine;

namespace KerbalSpaceNecoArc
{
    public class ShipInteriorModule: MonoBehaviour
    {
        public void Start()
        {
            // Replaces heads for all kerbals inside the ship's internal space
            // after it was loaded. See comments for TRIvaModelModule in
            // TextureReplacer's code (TRIvaModelModule.cs and Personaliser.cs)
            // for more details.
            foreach (Kerbal kerbal in GetComponentsInChildren<Kerbal>()) {
                if (kerbal.GetComponent<IvaModule>() == null) {
                    kerbal.gameObject.AddComponent<IvaModule>();
                }
            }

            Destroy(this);
        }
    }

    public class IvaModule: MonoBehaviour
    {
        public void Start()
        {
            var kerbal = GetComponent<Kerbal>();
            if (GetComponent<NecoArcHeadController>() == null)
            {
                var controller = gameObject.AddComponent<NecoArcHeadController>();
                controller.hideInFirstPerson = true;
                controller.kerbalName = kerbal != null && kerbal.protoCrewMember != null
                    ? kerbal.protoCrewMember.name : null;
            }
            Destroy(this);
        }
    }

    public class EvaModule: PartModule
    {
        private bool isInitialised = false;

        public override void OnStart(StartState state)
        {
            if (isInitialised) return;
            isInitialised = true;

            if (GetComponent<NecoArcHeadController>() == null)
            {
                var controller = gameObject.AddComponent<NecoArcHeadController>();
                controller.kerbalName = CrewName();
            }
            UpdateToggleName();
        }

        private string CrewName()
        {
            return part != null && part.protoModuleCrew != null && part.protoModuleCrew.Count > 0
                ? part.protoModuleCrew[0].name : null;
        }

        // Shown in the EVA kerbal's right-click menu, alongside "Remove Helmet".
        [KSPEvent(guiActive = true, guiActiveUnfocused = true, unfocusedRange = 5f, guiName = "Hide Neco Arc Head")]
        public void ToggleNecoArcHead()
        {
            NecoArcConfig.ToggleFor(CrewName());
            UpdateToggleName();
        }

        private void UpdateToggleName()
        {
            var ev = Events["ToggleNecoArcHead"];
            if (ev != null)
            {
                ev.guiName = NecoArcConfig.IsEnabledFor(CrewName())
                    ? "Hide Neco Arc Head" : "Show Neco Arc Head";
            }
        }
    }
}
