import type { Wireframe } from "@/lib/sections";

const bar = "rounded bg-muted";

function Table() {
  return (
    <div className="space-y-3">
      <div className="h-3 w-full rounded bg-muted-foreground/15" />
      {[1, 2, 3, 4].map((row) => (
        <div key={row} className="grid grid-cols-4 gap-4">
          <div className={`${bar} col-span-2 h-3`} />
          <div className={`${bar} h-3`} />
          <div className={`${bar} h-3`} />
        </div>
      ))}
    </div>
  );
}

function Cards() {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {[1, 2, 3].map((card) => (
        <div key={card} className="space-y-2 rounded-lg border p-3">
          <div className={`${bar} h-3 w-2/3`} />
          <div className={`${bar} h-2 w-full`} />
          <div className={`${bar} h-2 w-5/6`} />
          <div className={`${bar} mt-3 h-6 w-1/2`} />
        </div>
      ))}
    </div>
  );
}

function Calendar() {
  return (
    <div className="grid grid-cols-7 gap-1.5">
      {Array.from({ length: 21 }, (_, day) => (
        <div key={day} className="flex h-12 flex-col gap-1 rounded border p-1">
          <div className={`${bar} h-1.5 w-3`} />
          {day % 5 === 1 ? <div className="h-2 rounded bg-primary/20" /> : null}
        </div>
      ))}
    </div>
  );
}

function Chart() {
  const heights = ["h-1/3", "h-1/2", "h-2/5", "h-2/3", "h-3/5", "h-4/5", "h-3/4"];
  return (
    <div className="flex h-32 items-end gap-3 border-b pb-px">
      {heights.map((height, index) => (
        <div key={index} className={`${height} flex-1 rounded-t bg-primary/15`} />
      ))}
    </div>
  );
}

function Split() {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="space-y-2 rounded-lg border p-3">
        {[1, 2, 3, 4].map((row) => (
          <div key={row} className={`${bar} h-3`} />
        ))}
      </div>
      <div className="space-y-2 rounded-lg border p-3 sm:col-span-2">
        <div className={`${bar} h-3 w-1/2`} />
        {[1, 2, 3, 4, 5].map((row) => (
          <div key={row} className={`${bar} h-2`} />
        ))}
      </div>
    </div>
  );
}

function Timeline() {
  return (
    <div className="space-y-3">
      <div className={`${bar} mx-auto h-24 w-full max-w-sm`} />
      <div className="flex gap-1.5">
        <div className="h-8 flex-[2] rounded bg-primary/20" />
        <div className="h-8 flex-[3] rounded bg-primary/15" />
        <div className="h-8 flex-1 rounded bg-primary/10" />
        <div className="h-8 flex-[2] rounded bg-primary/15" />
      </div>
      <div className={`${bar} h-4`} />
    </div>
  );
}

const WIREFRAMES = {
  table: Table,
  cards: Cards,
  calendar: Calendar,
  chart: Chart,
  split: Split,
  timeline: Timeline,
};

/** A decorative outline of a future screen. It holds no data, and screen readers skip it. */
export function WireframePreview({ kind }: { kind: Wireframe }) {
  const Shape = WIREFRAMES[kind];
  return (
    <div aria-hidden="true" className="select-none opacity-70">
      <Shape />
    </div>
  );
}
