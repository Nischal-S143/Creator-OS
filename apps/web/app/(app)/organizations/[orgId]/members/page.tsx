"use client";

import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { useOrg } from "@/components/org-shell";
import { PageHeader } from "@/components/page-header";
import { ErrorState, LoadingRows } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  ApiError,
  ROLE_LABELS,
  api,
  can,
  useResource,
  type Member,
  type Page,
  type Role,
} from "@/lib/api";

const selectClass =
  "h-8 rounded-lg border border-input bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50";

function RoleSelect({
  id,
  value,
  actorRole,
  label,
  onChange,
}: {
  id?: string;
  value: Role;
  actorRole: Role;
  label?: string;
  onChange: (role: Role) => void;
}) {
  const roles = (Object.keys(ROLE_LABELS) as Role[]).filter(
    (role) => role !== "owner" || actorRole === "owner" || value === "owner",
  );
  return (
    <select
      id={id}
      aria-label={label}
      className={selectClass}
      value={value}
      onChange={(event) => onChange(event.target.value as Role)}
    >
      {roles.map((role) => (
        <option key={role} value={role}>
          {ROLE_LABELS[role]}
        </option>
      ))}
    </select>
  );
}

function Members({ path, role }: { path: string; role: Role }) {
  const { data, error, loading, reload } = useResource<Page<Member>>(`${path}?limit=100`);
  const [email, setEmail] = useState("");
  const [newRole, setNewRole] = useState<Role>("editor");
  const [busy, setBusy] = useState(false);
  const [removing, setRemoving] = useState<Member | null>(null);
  const manage = can.manageMembers(role);

  async function add(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api<Member>(path, { method: "POST", body: { email, role: newRole } });
      toast.success(`Added ${email}`);
      setEmail("");
      reload();
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not add the member.");
    } finally {
      setBusy(false);
    }
  }

  async function update(member: Member, body: { role?: Role; status?: Member["status"] }) {
    try {
      await api<Member>(`${path}/${member.id}`, { method: "PATCH", body });
      toast.success(`Updated ${member.email}`);
    } catch (caught) {
      toast.error(caught instanceof ApiError ? caught.message : "Could not update the member.");
    }
    reload();
  }

  if (loading) return <LoadingRows />;
  if (error) return <ErrorState message={error.message} onRetry={reload} />;

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                {manage ? <TableHead className="text-right">Action</TableHead> : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items.map((member) => {
                const locked = member.role === "owner" && role !== "owner";
                return (
                  <TableRow key={member.id}>
                    <TableCell className="max-w-64 truncate">{member.email}</TableCell>
                    <TableCell>
                      {manage && member.status === "active" && !locked ? (
                        <RoleSelect
                          label={`Role for ${member.email}`}
                          value={member.role}
                          actorRole={role}
                          onChange={(next) => update(member, { role: next })}
                        />
                      ) : (
                        ROLE_LABELS[member.role]
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={member.status === "active" ? "secondary" : "outline"}>
                        {member.status === "active" ? "Active" : "Removed"}
                      </Badge>
                    </TableCell>
                    {manage ? (
                      <TableCell className="text-right">
                        {locked ? null : member.status === "active" ? (
                          <Button variant="outline" size="sm" onClick={() => setRemoving(member)}>
                            Remove
                          </Button>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => update(member, { status: "active" })}
                          >
                            Restore
                          </Button>
                        )}
                      </TableCell>
                    ) : null}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {manage ? (
        <Card>
          <CardHeader>
            <CardTitle>Add a member</CardTitle>
            <CardDescription>They need a CreatorOS account first.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={add} className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="flex-1 space-y-2">
                <Label htmlFor="member-email">Email</Label>
                <Input
                  id="member-email"
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="member-role">Role</Label>
                <div>
                  <RoleSelect
                    id="member-role"
                    value={newRole}
                    actorRole={role}
                    onChange={setNewRole}
                  />
                </div>
              </div>
              <Button type="submit" disabled={busy}>
                {busy ? "Adding…" : "Add member"}
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : null}

      <Dialog open={removing !== null} onOpenChange={(open) => !open && setRemoving(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove this member?</DialogTitle>
            <DialogDescription>
              {removing?.email} loses access to this agency immediately. You can restore them later.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoving(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (removing) update(removing, { status: "removed" });
                setRemoving(null);
              }}
            >
              Remove member
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function MembersPage() {
  const organization = useOrg();
  return (
    <>
      <PageHeader title="Members" description="People in this agency and what they can do." />
      {can.viewMembers(organization.role) ? (
        <Members path={`/organizations/${organization.id}/members`} role={organization.role} />
      ) : (
        <ErrorState message="Your role cannot view members." />
      )}
    </>
  );
}
