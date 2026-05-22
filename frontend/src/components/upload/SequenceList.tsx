"use client";

import { DndContext, closestCenter, DragEndEvent } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy, useSortable, arrayMove } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Clip } from "@/lib/types";
import { ClipCard } from "./ClipCard";

interface SortableClipProps {
  clip: Clip;
  onDelete?: () => void;
}

function SortableClip({ clip, onDelete }: SortableClipProps) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: clip.id });
  const style = { transform: CSS.Transform.toString(transform), transition };

  return (
    <div ref={setNodeRef} style={style}>
      <ClipCard clip={clip} onDelete={onDelete} dragHandleProps={{ ...attributes, ...listeners }} />
    </div>
  );
}

interface SequenceListProps {
  clips: Clip[];
  onReorder: (clips: Clip[]) => void;
  onDelete?: (clipId: string) => void;
}

export function SequenceList({ clips, onReorder, onDelete }: SequenceListProps) {
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = clips.findIndex((c) => c.id === active.id);
    const newIndex = clips.findIndex((c) => c.id === over.id);
    const reordered = arrayMove(clips, oldIndex, newIndex);
    onReorder(reordered);
  };

  return (
    <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={clips.map((c) => c.id)} strategy={verticalListSortingStrategy}>
        <div className="space-y-2">
          {clips.map((clip) => (
            <SortableClip key={clip.id} clip={clip} onDelete={onDelete ? () => onDelete(clip.id) : undefined} />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}
