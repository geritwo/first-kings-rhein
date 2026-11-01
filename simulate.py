"""
Headless simulation: run the rules for N seasons with no UI and print a summary.
Useful for balancing (growth speed, spoilage, AU income) without clicking.

    python simulate.py [turns] [seed]
"""

import sys

from world import LOYALTY, POP_NAMES, RELIGION, World


def summary(w):
    print(f"\n=== {w.date_str()} | ezüst {w.silver:.0f} | presztízs {w.prestige} "
          f"| tekintély {w.au} ===")
    for p in sorted(w.provinces, key=lambda p: (not p.is_player, p.faction, p.name)):
        pops = [0, 0, 0, 0]
        for h in p.settled:
            pops[w.tiles[h].pop] += 1
        status = {"royal": "királyi", "vassal": "vazallus"}.get(p.status, p.faction)
        loyal = f" {LOYALTY[p.loyalty]:<11}" if p.is_player else " " * 12
        proj = p.project["label"] if p.project else "-"
        print(f"{p.name:<12} {status:<9}{loyal} {RELIGION[p.religion]:<10} "
              f"raktár {p.store:5.1f}  "
              + " ".join(f"{POP_NAMES[i][:4]}:{pops[i]}" for i in range(1, 4))
              + f"  lovag {w.knights(p)}  terület {len(p.territory):3}  projekt: {proj}")


def main():
    turns = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    w = World(seed=seed)
    summary(w)
    for _ in range(turns):
        # the player's own provinces are left idle here; NPC lords act
        w.end_turn()
    summary(w)
    print("\nNapló (utolsó 10):")
    for line in w.log[-10:]:
        print("  " + line)


if __name__ == "__main__":
    main()
