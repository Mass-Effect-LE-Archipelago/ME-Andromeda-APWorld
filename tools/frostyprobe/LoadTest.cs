// Diagnose why Frosty assemblies refuse to load, trying several load paths.
using System;
using System.IO;
using System.Reflection;

static class LoadTest
{
    static void Try(string label, Func<Assembly> f)
    {
        try
        {
            Assembly a = f();
            Type[] ts = a.GetTypes();
            Console.WriteLine(label + " OK " + a.FullName + " types=" + ts.Length);
        }
        catch (Exception e)
        {
            Console.WriteLine(label + " FAIL " + e.GetType().FullName + " 0x" + e.HResult.ToString("X8") + " :: " + e.Message);
            if (e.InnerException != null) Console.WriteLine("   inner: " + e.InnerException.Message);
            ReflectionTypeLoadException rt = e as ReflectionTypeLoadException;
            if (rt != null)
                foreach (var le in rt.LoaderExceptions) Console.WriteLine("   loader: " + (le == null ? "null" : le.Message));
        }
    }

    static void Main(string[] args)
    {
        string path = args.Length > 0 ? args[0] : "FrostySdk.dll";
        Console.WriteLine("runtime " + Environment.Version + " 64bit=" + Environment.Is64BitProcess);
        Try("LoadFrom ", () => Assembly.LoadFrom(path));
        Try("LoadFile ", () => Assembly.LoadFile(path));
        Try("LoadBytes", () => Assembly.Load(File.ReadAllBytes(path)));
    }
}
