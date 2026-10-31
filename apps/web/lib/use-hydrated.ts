import { useSyncExternalStore } from "react";

const noSubscription = () => () => {};

/** False in server-rendered HTML, true once the page is interactive. */
export function useHydrated() {
  return useSyncExternalStore(
    noSubscription,
    () => true,
    () => false,
  );
}
