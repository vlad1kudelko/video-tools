import { BaseEdge, EdgeLabelRenderer, getStraightPath } from "@xyflow/react";

export default function DeletableEdge({ id, sourceX, sourceY, targetX, targetY, style, markerEnd, data }) {
  // A straight line's midpoint is exact and trivial — getBezierPath's label
  // point is only an approximation of the curve's center and visibly drifts
  // off the actual path for steep/asymmetric connections.
  const [edgePath, labelX, labelY] = getStraightPath({ sourceX, sourceY, targetX, targetY });

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={style} markerEnd={markerEnd} />
      <EdgeLabelRenderer>
        <button
          onClick={(e) => {
            e.stopPropagation();
            data?.onDelete?.(id);
          }}
          title="Разорвать связь"
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: "all",
          }}
          className="flex h-5 w-5 items-center justify-center rounded-full border border-neutral-600 bg-neutral-800 text-xs leading-none text-neutral-300 transition-colors hover:border-red-500 hover:bg-red-600 hover:text-white"
        >
          ×
        </button>
      </EdgeLabelRenderer>
    </>
  );
}
