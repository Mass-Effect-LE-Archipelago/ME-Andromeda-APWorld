// Dumps the public API surface of the Frosty assemblies.
// The CLR refuses LoadFrom here ("network location"), so assemblies are loaded from
// bytes and dependencies are resolved from the same directory.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;

static class Reflect
{
    static string Dir;

    static Assembly LoadBytes(string path)
    {
        return Assembly.Load(File.ReadAllBytes(path));
    }

    static Assembly Resolve(object sender, ResolveEventArgs args)
    {
        string name = new AssemblyName(args.Name).Name + ".dll";
        string p = Path.Combine(Dir, name);
        return File.Exists(p) ? LoadBytes(p) : null;
    }

    static void Main(string[] args)
    {
        Dir = args.Length > 0 ? args[0] : Directory.GetCurrentDirectory();
        AppDomain.CurrentDomain.AssemblyResolve += Resolve;
        string outPath = args.Length > 1 ? args[1] : "frosty-api.txt";
        var sb = new StringBuilder();
        foreach (string path in Directory.GetFiles(Dir, "*.dll").OrderBy(x => x))
        {
            string leaf = Path.GetFileName(path);
            if (leaf.StartsWith("SharpDX") || leaf.StartsWith("NAudio") || leaf.StartsWith("Newtonsoft") ||
                leaf.StartsWith("discord") || leaf == "CryptBase.dll") continue;
            Assembly asm;
            try { asm = LoadBytes(path); }
            catch (Exception e) { sb.AppendLine("LOAD FAILED " + Path.GetFileName(path) + " :: " + e.Message); continue; }
            sb.AppendLine("=== " + asm.GetName().Name + " " + asm.GetName().Version + " ===");
            Type[] types;
            try { types = asm.GetTypes(); }
            catch (ReflectionTypeLoadException e) { types = e.Types.Where(t => t != null).ToArray(); }
            foreach (Type t in types.OrderBy(t => t.FullName))
            {
                if (!t.IsPublic && !t.IsNestedPublic) continue;
                sb.AppendLine("TYPE " + t.FullName + (t.IsEnum ? " (enum)" : t.IsInterface ? " (interface)" : ""));
                if (t.IsEnum) continue;
                foreach (var c in t.GetConstructors())
                    sb.AppendLine("  ctor(" + string.Join(", ", c.GetParameters().Select(p => p.ParameterType.Name + " " + p.Name)) + ")");
                foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly))
                {
                    if (m.IsSpecialName) continue;
                    sb.AppendLine("  " + (m.IsStatic ? "static " : "") + m.ReturnType.Name + " " + m.Name + "(" +
                                  string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name + " " + p.Name)) + ")");
                }
                foreach (var p in t.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly))
                    sb.AppendLine("  prop " + p.PropertyType.Name + " " + p.Name);
                foreach (var f in t.GetFields(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly))
                    sb.AppendLine("  field " + f.FieldType.Name + " " + f.Name);
            }
        }
        File.WriteAllText(outPath, sb.ToString());
        Console.WriteLine("wrote " + outPath + " (" + sb.Length + " chars)");
    }
}
