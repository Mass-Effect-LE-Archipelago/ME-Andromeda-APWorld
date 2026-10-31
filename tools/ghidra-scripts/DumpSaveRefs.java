// After full analysis: report references to the save/plot anchor strings and list
// functions whose names look like plot or save plumbing.
// @category MEAP

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.DataType;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

public class DumpSaveRefs extends GhidraScript {

    private static final String[] ANCHORS = {
        "BioMetrics_PlotStartMarker", "PlotSaveGameAgent", "FBCHUNKS", "FBHEADER",
        "PlotFlagIds", "PlotFlagsDefaultValues", "NewGamePlusPlotFlags", "PlotFlagDebugSymbol",
        "LastPlotFlagSet", "IPlotFlag", "BooleanPlotFlag", "IntegerPlotFlag", "FloatPlotFlag"
    };

    @Override
    public void run() throws Exception {
        String outPath = System.getenv("MEAP_RE_OUT");
        if (outPath == null) {
            outPath = "dump-save-refs.txt";
        }
        PrintWriter out = new PrintWriter(outPath, "UTF-8");
        try {
            out.println("program: " + currentProgram.getName());
            out.println();

            DataIterator it = currentProgram.getListing().getDefinedData(true);
            int stringCount = 0;
            while (it.hasNext()) {
                Data d = it.next();
                Object v = d.getValue();
                if (!(v instanceof String)) {
                    continue;
                }
                String s = (String) v;
                stringCount++;
                for (String anchor : ANCHORS) {
                    if (!s.contains(anchor)) {
                        continue;
                    }
                    Address a = d.getAddress();
                    out.println("ANCHOR " + anchor + "  string=" + s + "  at " + a);
                    ReferenceIterator refs = getReferencesTo(a);
                    int n = 0;
                    while (refs.hasNext()) {
                        Reference r = refs.next();
                        Address from = r.getFromAddress();
                        Function f = getFunctionContaining(from);
                        String fn = (f == null) ? "<no function>" : (f.getName() + " @ " + f.getEntryPoint());
                        out.println("    ref " + from + "  type=" + r.getReferenceType() + "  " + fn);
                        if (++n >= 40) {
                            out.println("    ... more refs omitted");
                            break;
                        }
                    }
                }
            }
            out.println();
            out.println("defined strings scanned: " + stringCount);
            out.println();

            List<String> interesting = new ArrayList<>();
            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            while (functions.hasNext()) {
                Function f = functions.next();
                String name = f.getName();
                String lower = name.toLowerCase();
                if (lower.contains("plot") || lower.contains("savegame") || lower.contains("profsave")
                        || lower.contains("persistence")) {
                    interesting.add(f.getEntryPoint() + "  " + name + "  params=" + f.getParameterCount()
                            + "  body=" + f.getBody().getNumAddresses());
                }
            }
            out.println("interesting functions: " + interesting.size());
            for (String s : interesting) {
                out.println("  " + s);
            }
        } finally {
            out.close();
        }
        println("wrote " + outPath);
    }
}
