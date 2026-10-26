import { describe, expect, it, vi } from "vitest";
import { createApiClient } from "./api";
import { defaultState } from "./storage";


describe("Sweety API client", () => {
  it("loads the application state", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(defaultState), { status: 200 }));
    const client = createApiClient(fetcher);

    await expect(client.loadState()).resolves.toEqual(defaultState);
    expect(fetcher).toHaveBeenCalledWith("/api/state", expect.objectContaining({ headers: { Accept: "application/json" } }));
  });

  it("loads sanitized About Sweety content", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ html: "<main>About</main>" }), { status: 200 }));
    const client = createApiClient(fetcher);

    await expect(client.loadAbout()).resolves.toEqual({ html: "<main>About</main>" });
    expect(fetcher).toHaveBeenCalledWith("/api/about", expect.objectContaining({ headers: { Accept: "application/json" } }));
  });

  it("loads the shared startup update result", async () => {
    const update = { checked: true, updateAvailable: false };
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(update), { status: 200 }));
    const client = createApiClient(fetcher);

    await expect(client.updateStatus()).resolves.toEqual(update);
    expect(fetcher).toHaveBeenCalledWith(
      "/api/update",
      expect.objectContaining({ headers: { Accept: "application/json" } }),
    );
  });

  it("persists a complete state snapshot", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(defaultState), { status: 200 }));
    const client = createApiClient(fetcher);

    await client.saveState(defaultState);

    expect(fetcher).toHaveBeenCalledWith("/api/state", expect.objectContaining({ method: "PUT" }));
  });

  it("surfaces stable API errors", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: "duplicate_target_name", message: "Name exists" }), { status: 409 }),
    );
    const client = createApiClient(fetcher);

    await expect(client.saveState(defaultState)).rejects.toThrow("Name exists");
  });
});
