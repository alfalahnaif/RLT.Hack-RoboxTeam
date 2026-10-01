import { Card, CardBody } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/** Loading placeholder for a result card (S-02 loading state). */
export function ResultCardSkeleton() {
  return (
    <Card aria-hidden>
      <CardBody className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <Skeleton className="size-10 rounded-md" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-3 w-1/3" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 md:max-w-[360px]">
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
        </div>
        <Skeleton className="h-3 w-2/3" />
        <Skeleton className="h-3 w-1/2" />
      </CardBody>
    </Card>
  );
}

/** Generic stacked-cards placeholder (profile / compare / history). */
export function PageSkeleton({ blocks = 3 }: { blocks?: number }) {
  return (
    <div className="flex flex-col gap-4" aria-hidden>
      {Array.from({ length: blocks }, (_, i) => (
        <Card key={i}>
          <CardBody className="flex flex-col gap-3">
            <Skeleton className="h-5 w-1/4" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-5/6" />
            <Skeleton className="h-3 w-2/3" />
          </CardBody>
        </Card>
      ))}
    </div>
  );
}
