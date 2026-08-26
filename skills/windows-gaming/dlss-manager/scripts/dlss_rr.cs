// dlss_rr.cs — driver-level DLSS Ray Reconstruction preset override via NVAPI DRS.
// Compiled with the built-in .NET Framework csc.exe (no installs, C# 5 compatible):
//   C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /nologo /out:dlss_rr.exe dlss_rr.cs
// Runs from cmd.exe / WSL interop. Same mechanism as NVIDIA App "DLSS Override" /
// DLSS Swapper, but per-game by exe. Struct layouts mirror NvAPIWrapper.Net 0.8.1.101:
// DRSSettingV1=12320B, DRSApplicationV4=20492B, DRSProfileV1=4116B, version field =
// (major << 16) | struct_size, UnicodeString = 2048 wchars, value union = 4100B.
//
// Usage:
//   dlss_rr.exe <exe_name> read
//   dlss_rr.exe <exe_name> set <decimal>     # also sets enable flag 0x10E41E02=1
//   dlss_rr.exe <exe_name> unset             # removes preset + enable flag
// Output: "RR=<0xHEX|unset>"
using System;
using System.Runtime.InteropServices;

static class DlssRr
{
    const uint RR_PRESET_ID = 0x10E41DF7;
    const uint RR_ENABLE_ID = 0x10E41E02;
    const int OK = 0;
    const int SETTING_NOT_FOUND = -160;
    const int PROFILE_NOT_FOUND = -163;
    const int NLEN = 2048;

    // nvapi64.dll exports are ordinal-only except nvapi_QueryInterface.
    [DllImport("nvapi64", EntryPoint = "nvapi_QueryInterface", CallingConvention = CallingConvention.Cdecl)]
    static extern IntPtr QueryInterface(uint id);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Fn_Initialize();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Fn_Unload();
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Fn_CreateSession(out IntPtr session);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Fn_LoadSettings(IntPtr session);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Fn_SaveSettings(IntPtr session);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Fn_DestroySession(IntPtr session);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Fn_FindApplicationByName(IntPtr session, [MarshalAs(UnmanagedType.LPWStr)] string appName, out IntPtr profile, ref DRSApplicationV4 app);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Fn_CreateProfile(IntPtr session, ref DRSProfileV1 profile, out IntPtr handle);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Fn_CreateApplication(IntPtr session, IntPtr profile, ref DRSApplicationV4 app);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Fn_GetSetting(IntPtr session, IntPtr profile, uint id, ref DRSSettingV1 setting);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Fn_SetSetting(IntPtr session, IntPtr profile, ref DRSSettingV1 setting);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Fn_DeleteProfileSetting(IntPtr session, IntPtr profile, uint id);

    [StructLayout(LayoutKind.Sequential)]
    struct DRSSettingValue
    {
        public uint Value;                                  // u32 at offset 0 (union start)
        [MarshalAs(UnmanagedType.ByValArray, SizeConst = 4096)]
        public byte[] Rest;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode, Pack = 8)]
    struct DRSSettingV1
    {
        public uint version;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = NLEN)]
        public string settingName;
        public uint settingId;
        public uint settingType;
        public uint settingLocation;
        public uint isCurrentPredefined;
        public uint isPredefinedValid;
        public DRSSettingValue predefinedValue;
        public DRSSettingValue currentValue;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode, Pack = 8)]
    struct DRSApplicationV4
    {
        public uint version;
        public uint isPredefined;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = NLEN)]
        public string applicationName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = NLEN)]
        public string friendlyName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = NLEN)]
        public string launcherName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = NLEN)]
        public string fileInFolder;
        public uint flags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = NLEN)]
        public string commandLine;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode, Pack = 8)]
    struct DRSProfileV1
    {
        public uint version;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = NLEN)]
        public string profileName;
        public uint gpuSupport;
        public uint isPredefined;
        public uint numOfApps;
        public uint numOfSettings;
    }

    static T GetFn<T>(uint hash) where T : class
    {
        IntPtr p = QueryInterface(hash);
        if (p == IntPtr.Zero) throw new Exception("nvapi_QueryInterface NULL for 0x" + hash.ToString("X"));
        return (T)(object)Marshal.GetDelegateForFunctionPointer(p, typeof(T));
    }

    static uint StructVersion(int major, Type t)
    {
        return (uint)((major << 16) | Marshal.SizeOf(t));
    }

    static IntPtr FindProfile(Fn_FindApplicationByName findApp, IntPtr session, uint appVer, string exeName)
    {
        IntPtr profile;
        DRSApplicationV4 app = new DRSApplicationV4();
        app.version = appVer;
        int rc = findApp(session, exeName, out profile, ref app);
        if (rc == PROFILE_NOT_FOUND) return IntPtr.Zero;
        if (rc != OK) throw new Exception("FindApplicationByName(" + exeName + ") failed: " + rc);
        return profile;
    }

    static void SetOne(Fn_SetSetting setSetting, IntPtr session, IntPtr profile, uint setVer, uint id, uint value)
    {
        DRSSettingV1 s = new DRSSettingV1();
        s.version = setVer;
        s.settingId = id;
        s.settingType = 0;      // DRSSettingType.Integer
        s.settingLocation = 0;  // DRSSettingLocation.CurrentProfile
        s.isCurrentPredefined = 0;
        s.isPredefinedValid = 0;
        DRSSettingValue v = new DRSSettingValue();
        v.Value = value;
        v.Rest = new byte[4096];
        s.currentValue = v;
        int rc = setSetting(session, profile, ref s);
        if (rc != OK) throw new Exception("SetSetting(0x" + id.ToString("X") + "=" + value + ") failed: " + rc);
    }

    static int Main(string[] args)
    {
        try
        {
            if (args.Length < 2) { Console.Error.WriteLine("usage: dlss_rr.exe <exe> read | set <value> | unset"); return 2; }
            string exe = args[0];
            string action = args[1].ToLowerInvariant();

            Fn_Initialize Init = GetFn<Fn_Initialize>(0x150E828);
            Fn_Unload Unload = GetFn<Fn_Unload>(0xD22BDD7E);
            Fn_CreateSession CreateSession = GetFn<Fn_CreateSession>(0x694D52E);
            Fn_LoadSettings LoadSettings = GetFn<Fn_LoadSettings>(0x375DBD6B);
            Fn_SaveSettings SaveSettings = GetFn<Fn_SaveSettings>(0xFCBC7E14);
            Fn_DestroySession DestroySession = GetFn<Fn_DestroySession>(0xDAD9CFF8);
            Fn_FindApplicationByName FindApp = GetFn<Fn_FindApplicationByName>(0xEEE566B2);
            Fn_CreateProfile CreateProfile = GetFn<Fn_CreateProfile>(0xCC176068);
            Fn_CreateApplication CreateApplication = GetFn<Fn_CreateApplication>(0x4347A9DE);
            Fn_GetSetting GetSetting = GetFn<Fn_GetSetting>(0x73BF8338);
            Fn_SetSetting SetSetting = GetFn<Fn_SetSetting>(0x577DD202);
            Fn_DeleteProfileSetting DeleteSetting = GetFn<Fn_DeleteProfileSetting>(0xE4A26362);

            if (Init() != OK) { Console.Error.WriteLine("NvAPI_Initialize failed"); return 3; }
            IntPtr session;
            if (CreateSession(out session) != OK || session == IntPtr.Zero) { Console.Error.WriteLine("CreateSession failed"); return 4; }
            if (LoadSettings(session) != OK) { Console.Error.WriteLine("LoadSettings failed"); return 5; }

            uint appVer = StructVersion(4, typeof(DRSApplicationV4));
            uint profVer = StructVersion(1, typeof(DRSProfileV1));
            uint setVer = StructVersion(1, typeof(DRSSettingV1));

            if (action == "read")
            {
                IntPtr profile = FindProfile(FindApp, session, appVer, exe);
                uint? val = null;
                if (profile != IntPtr.Zero)
                {
                    DRSSettingV1 s = new DRSSettingV1();
                    s.version = setVer;
                    s.settingId = RR_PRESET_ID;
                    int rc = GetSetting(session, profile, RR_PRESET_ID, ref s);
                    if (rc == OK) val = s.currentValue.Value;
                    else if (rc != SETTING_NOT_FOUND) throw new Exception("GetSetting failed: " + rc);
                }
                // 0 == Default == no effective override (driver keeps a 0-valued entry after delete)
                Console.WriteLine(val.HasValue && val.Value != 0 ? "RR=0x" + val.Value.ToString("X8") : "RR=unset");
                return 0;
            }

            if (action == "set")
            {
                if (args.Length < 3) { Console.Error.WriteLine("set needs a value"); return 2; }
                uint value = uint.Parse(args[2]);
                IntPtr profile = FindProfile(FindApp, session, appVer, exe);
                if (profile == IntPtr.Zero)
                {
                    DRSProfileV1 p = new DRSProfileV1();
                    p.version = profVer;
                    p.profileName = exe.Replace(".exe", "");
                    p.gpuSupport = 0;
                    p.isPredefined = 0;
                    p.numOfApps = 0;
                    p.numOfSettings = 0;
                    int rc = CreateProfile(session, ref p, out profile);
                    if (rc != OK) throw new Exception("CreateProfile failed: " + rc);
                    DRSApplicationV4 a = new DRSApplicationV4();
                    a.version = appVer;
                    a.isPredefined = 0;
                    a.applicationName = exe;
                    a.friendlyName = exe;
                    a.launcherName = "";
                    a.fileInFolder = "";
                    a.flags = 0;
                    a.commandLine = "";
                    rc = CreateApplication(session, profile, ref a);
                    if (rc != OK) throw new Exception("CreateApplication failed: " + rc);
                }
                SetOne(SetSetting, session, profile, setVer, RR_PRESET_ID, value);
                SetOne(SetSetting, session, profile, setVer, RR_ENABLE_ID, 1);   // enable flag — preset-only can be silently ignored (Halo)
                SaveSettings(session);
                Console.WriteLine("RR=0x" + value.ToString("X8"));
                return 0;
            }

            if (action == "unset")
            {
                IntPtr profile = FindProfile(FindApp, session, appVer, exe);
                if (profile != IntPtr.Zero)
                {
                    uint[] ids = new uint[] { RR_PRESET_ID, RR_ENABLE_ID };
                    for (int i = 0; i < ids.Length; i++)
                    {
                        int rc = DeleteSetting(session, profile, ids[i]);
                        if (rc != OK && rc != SETTING_NOT_FOUND) throw new Exception("DeleteSetting(0x" + ids[i].ToString("X") + ") failed: " + rc);
                    }
                    SaveSettings(session);
                }
                Console.WriteLine("RR=unset");
                return 0;
            }

            Console.Error.WriteLine("unknown action: " + action);
            return 2;
        }
        catch (Exception e)
        {
            Console.Error.WriteLine("dlss_rr: " + e.Message);
            return 1;
        }
    }
}
