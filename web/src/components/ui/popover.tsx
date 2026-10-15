"use client";

import * as React from "react";
import * as P from "@radix-ui/react-popover";
import { cn } from "@/lib/utils";

export const Popover = P.Root;
export const PopoverTrigger = P.Trigger;

export function PopoverContent({ className, ...props }: React.ComponentPropsWithoutRef<typeof P.Content>) {
  return (
    <P.Portal>
      <P.Content
        sideOffset={6}
        collisionPadding={12}
        className={cn("z-50 w-[min(26rem,calc(100vw-2rem))] rounded-md border bg-surface p-4 text-sm shadow-lg outline-none", className)}
        {...props}
      />
    </P.Portal>
  );
}
