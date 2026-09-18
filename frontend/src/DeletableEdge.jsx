import { useState } from "react";
import { BaseEdge, EdgeLabelRenderer, getBezierPath } from "@xyflow/react";
import { CrossIcon } from "./nodeShared.jsx";

export default function DeletableEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
  data,
}) {
  const [hovered, setHovered] = useState(false);
  const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition });

  return (
    <>
      <BaseEdge id={id} path={edgePath} style={style} markerEnd={markerEnd} />
      {/* Invisible wide hit-area over the (thin) curve — hovering anywhere
          near the line reveals the delete button, not just a hairline. */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={20}
        style={{ cursor: "pointer" }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      />
      <EdgeLabelRenderer>
        <button
          onClick={(e) => {
            e.stopPropagation();
            data?.onDelete?.(id);
          }}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          title="Разорвать связь"
          style={{
            position: "absolute",
            // Center of the curve — only ever shown on hover now, so the
            // earlier lag (an animated transform racing the drag) doesn't
            // apply here; only opacity fades.
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            opacity: hovered ? 1 : 0,
            pointerEvents: hovered ? "all" : "none",
          }}
          className="flex h-5 w-5 items-center justify-center rounded-full border border-neutral-600 bg-neutral-800 text-neutral-300 transition-opacity hover:border-red-500 hover:bg-red-600 hover:text-white"
        >
          <CrossIcon />
        </button>
      </EdgeLabelRenderer>
    </>
  );
}
