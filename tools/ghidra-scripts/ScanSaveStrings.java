// Scans initialized memory for ASCII strings matching save/plot related patterns.
// Runs without analysis (-noanalysis), so it is fast even on a 75 MB executable.
// @category MEAP

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;

import java.util.ArrayList;
import java.util.List;

public class ScanSaveStrings extends GhidraScript {

    private static final String[] NEEDLES = {
        "BioMetrics", "biometrics", "plotflag", "PlotFlag", "PlotSaveGame", "SaveGameAgent",
        "FBCHUNKS", "FBHEADER", "PROFSAVE", "Profsave", "PlotBlock", "SaveGame_",
        "SaveGameAgent", "JournalSystem", "GalaxyDataManager", "EventTracker", "CodexList",
        "WorldStateManager", "VendorInventory", "PartyManager", "ActivePlayTimer", "LootContainer",
        "Notifications", "DestructionManager", "WorldMap"
    };

    @Override
    public void run() throws Exception {
        Memory memory = currentProgram.getMemory();
        List<String> hits = new ArrayList<>();
        for (MemoryBlock block : memory.getBlocks()) {
            if (!block.isInitialized()) {
                continue;
            }
            long start = block.getStart().getOffset();
            long size = block.getSize();
            byte[] buf = new byte[(int) Math.min(size, Integer.MAX_VALUE)];
            try {
                memory.getBytes(block.getStart(), buf);
            } catch (Exception e) {
                println("skip block " + block.getName() + ": " + e.getMessage());
                continue;
            }
            int i = 0;
            while (i < buf.length) {
                int c = buf[i] & 0xFF;
                if (c >= 0x20 && c < 0x7F) {
                    int j = i;
                    while (j < buf.length) {
                        int d = buf[j] & 0xFF;
                        if (d < 0x20 || d >= 0x7F) {
                            break;
                        }
                        j++;
                    }
                    if (j - i >= 5) {
                        String s = new String(buf, i, j - i, "US-ASCII");
                        for (String needle : NEEDLES) {
                            if (s.contains(needle)) {
                                Address a = block.getStart().add(i);
                                hits.add(a + "  " + s);
                                break;
                            }
                        }
                    }
                    i = j;
                } else {
                    i++;
                }
            }
        }
        println("=== " + hits.size() + " matching strings ===");
        for (String h : hits) {
            println(h);
        }
    }
}
