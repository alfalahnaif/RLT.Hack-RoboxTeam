"use client";

import { useState, type ReactNode } from "react";
import {
  BellIcon,
  CalendarClockIcon,
  CloudDownloadIcon,
  EyeIcon,
  FilePdfIcon,
  FilterIcon,
  GoogleIcon,
  icons,
  LockIcon,
  LogoutIcon,
  MoreVerticalIcon,
  PenIcon,
  PlusIcon,
  SearchIcon,
  SettingsIcon,
  SproutIcon,
  TrashIcon,
  UserCircleIcon,
  CreditCardIcon,
  CopyIcon,
  BrowserSearchIcon,
  HomeIcon,
  ShieldInfoIcon,
  KeyIcon,
  BuildingIcon,
  UsersIcon,
  FaceFrownIcon,
} from "@/components/icons";
import { AppShell } from "@/components/layout/app-shell";
import { AccountButton, Header, HeaderIconButton } from "@/components/layout/header";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Alert } from "@/components/ui/alert";
import { Badge, CountBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox, CheckboxCard, CheckboxLabel } from "@/components/ui/checkbox";
import { Combobox } from "@/components/ui/combobox";
import { Calendar, DatePicker } from "@/components/ui/date-picker";
import { ConfirmDialog, Dialog, DialogBody, DialogClose, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Drawer, DrawerBody, DrawerContent, DrawerFooter, DrawerHeader, DrawerSection, DrawerTitle, DrawerTrigger } from "@/components/ui/drawer";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { EmptyState } from "@/components/ui/empty-state";
import { Field, FieldGrid } from "@/components/ui/field";
import { Input, Textarea } from "@/components/ui/input";
import { NotificationItem, OptionCard, SettingCard } from "@/components/ui/list-cards";
import { OtpInput } from "@/components/ui/otp-input";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination, PageSize } from "@/components/ui/pagination";
import { PhoneInput } from "@/components/ui/phone-input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { RadioCard, RadioCards, RadioGroup, RadioItem } from "@/components/ui/radio-group";
import { SimpleSelect } from "@/components/ui/select";
import { Kbd, Separator } from "@/components/ui/separator";
import { SideNav, SideNavItem, SideNavSection } from "@/components/ui/side-nav";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { StatCard } from "@/components/ui/stat-card";
import { Switch, SwitchLabel } from "@/components/ui/switch";
import { Symbol } from "@/components/ui/symbol";
import {
  BulkActions,
  Table,
  TableActions,
  TableBody,
  TableCard,
  TableCell,
  TableCheckboxCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableMainCell,
  TableRow,
  TableToolbar,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsHeader, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToastProvider, useToast } from "@/components/ui/toast";
import { Tooltip } from "@/components/ui/tooltip";
import { FileDropzone, FileItem, ImageUpload } from "@/components/ui/upload";
import { CheckList } from "@/components/ui/check-list";
import { CompareCell, CompareHeadCell, CompareHeadRow, CompareRow, CompareSection, CompareTable } from "@/components/ui/compare-table";
import { ContributionList } from "@/components/ui/contribution-list";
import { EvidenceItem } from "@/components/ui/evidence-item";
import { ExternalLink } from "@/components/ui/external-link";
import { ScorePill, ScoreStat } from "@/components/ui/score";
import { sampleFooterNav, sampleNav } from "./nav";

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <Card id={id} className="mb-4 scroll-mt-20">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardBody className="flex flex-col gap-6">{children}</CardBody>
    </Card>
  );
}

function Row({ label, children }: { label?: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      {label ? <p className="text-xs font-medium text-muted">{label}</p> : null}
      <div className="flex flex-wrap items-center gap-3">{children}</div>
    </div>
  );
}

const scales = ["primary", "secondary", "success", "info", "warning", "danger"] as const;
const steps: Record<(typeof scales)[number], string[]> = {
  primary: ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "1000"],
  secondary: ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "1000"],
  success: ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"],
  info: ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"],
  warning: ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"],
  danger: ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"],
};
const grays = ["25", "50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "1000"];

function Swatch({ name }: { name: string }) {
  return (
    <div className="flex w-[84px] flex-col gap-1">
      <div className="h-10 rounded-md border border-line-subtle" style={{ background: `var(--color-${name})` }} />
      <span className="text-2xs text-muted" dir="ltr">
        {name}
      </span>
    </div>
  );
}

function ToastDemo() {
  const toast = useToast();
  return (
    <Row label="Toast">
      <Button variant="success" onClick={() => toast({ tone: "success", title: "Saved successfully" })}>
        Success
      </Button>
      <Button variant="info" onClick={() => toast({ tone: "info", title: "Info", description: "Data updated" })}>
        Info
      </Button>
      <Button variant="warning" onClick={() => toast({ tone: "warning", title: "Warning" })}>
        Warning
      </Button>
      <Button variant="danger" onClick={() => toast({ tone: "danger", title: "Something went wrong" })}>
        Error
      </Button>
    </Row>
  );
}

export function Gallery() {
  const [checked, setChecked] = useState<boolean | "indeterminate">(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState("all");
  const [otp, setOtp] = useState("12");
  const [date, setDate] = useState<Date | undefined>();
  const [country, setCountry] = useState<string>();
  const [phone, setPhone] = useState("912 345-67-89");
  const [selected, setSelected] = useState<string[]>(["1"]);
  const [text, setText] = useState("");

  const notifications = (
    <Popover>
      <PopoverTrigger asChild>
        <HeaderIconButton count={2} aria-label="notifications">
          <BellIcon />
        </HeaderIconButton>
      </PopoverTrigger>
      <PopoverContent className="w-[440px] max-w-[calc(100vw-32px)]">
        <div className="flex flex-col gap-2 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-medium text-heading">Alerts</h3>
            <Button variant="link" strong>
              Mark all as read
            </Button>
          </div>
          <Tabs defaultValue="all">
            <TabsList fullWidth>
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="orders">Searches</TabsTrigger>
              <TabsTrigger value="bookings">Contracts</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
        <NotificationItem unread icon={<CalendarClockIcon />} title="Supplier data refreshed 13 days ago" meta="by: system" date="11:41 PM - 2026/07/06" />
        <NotificationItem icon={<CalendarClockIcon />} title="Supplier data refreshed 14 days ago" meta="by: system" date="01:30 AM - 2026/07/05" />
        <div className="border-t border-line px-4 pt-2 pb-4 text-center text-sm text-heading">View all</div>
      </PopoverContent>
    </Popover>
  );

  const account = (
    <Popover>
      <PopoverTrigger asChild>
        <AccountButton name="OOO TechnoPanel" code="RlQ2HSej" />
      </PopoverTrigger>
      <PopoverContent className="w-64 p-3 shadow-soft">
        <div className="flex items-center gap-1.5">
          <Symbol size="lg" shape="circle" />
          <div>
            <p className="text-sm font-medium text-heading">OOO TechnoPanel</p>
            <p className="text-xs text-subtle">Analyst: Ivan Petrov</p>
          </div>
        </div>
        <div className="mt-2 flex gap-2">
          <Badge color="gray">
            <BrowserSearchIcon /> Preview
          </Badge>
          <Badge color="gray">
            <CopyIcon /> Copy link
          </Badge>
        </div>
        <Separator className="my-3" />
        {[
          [UserCircleIcon, "Profile"],
          [CreditCardIcon, "Plan"],
          [SettingsIcon, "Settings"],
        ].map(([I, l]) => {
          const Icon = I as typeof UserCircleIcon;
          return (
            <button key={l as string} className="flex w-full items-center gap-2 py-2 text-sm text-heading">
              <Icon className="size-5 text-gray-500" />
              {l as string}
              {l === "Plan" ? (
                <Badge color="gray" className="ms-auto">
                  <SproutIcon /> Start
                </Badge>
              ) : null}
            </button>
          );
        })}
        <Separator className="my-3" />
        <button className="flex w-full items-center gap-2 py-2 text-sm text-heading">
          <LogoutIcon className="size-4 text-gray-500" /> Log out
        </button>
      </PopoverContent>
    </Popover>
  );

  return (
    <ToastProvider>
      <AppShell nav={sampleNav} footerNav={sampleFooterNav} moreLabel="More" header={<Header searchPlaceholder="Search..." notifications={notifications} account={account} />}>
        <PageHeader
          title="Design system"
          description="Every color, type style and component in all its states — Reference for building screens"
          actions={
            <>
              <Button variant="secondary">
                <CloudDownloadIcon /> Import
              </Button>
              <Button>
                <PlusIcon /> Add supplier
              </Button>
            </>
          }
        />

        <Section id="colors" title="Colors">
          {scales.map((s) => (
            <Row key={s} label={s}>
              {steps[s].map((n) => (
                <Swatch key={n} name={`${s}-${n}`} />
              ))}
            </Row>
          ))}
          <Row label="gray">
            {grays.map((n) => (
              <Swatch key={n} name={`gray-${n}`} />
            ))}
          </Row>
          <Row label="semantic">
            {["heading", "body", "subtle", "muted", "disabled", "placeholder", "canvas", "surface-subtle", "line", "line-subtle", "line-strong", "focus", "orange", "pink", "purple"].map((n) => (
              <Swatch key={n} name={n} />
            ))}
          </Row>
        </Section>

        <Section id="type" title="Typography">
          <div className="flex flex-col gap-3">
            <p className="text-2xl font-medium text-heading">Free — 26/36 medium (plan price)</p>
            <p className="text-xl font-semibold text-heading">
              12,500 ₽ — 20/30 semibold (Value KPI)
            </p>
            <p className="text-lg font-medium text-heading">🚀 Ready for your first search? — 18/30 medium</p>
            <p className="text-base font-semibold text-heading">Strong title — 16/24 semibold</p>
            <p className="text-base font-medium text-heading">Page / card / dialog title — 16/24 medium</p>
            <p className="text-base text-muted">Empty state description — 16/24 regular muted</p>
            <p className="text-sm font-medium text-heading">Item title / table header — 14/22 medium</p>
            <p className="text-sm text-heading">Body text & table cells — 14/22 regular</p>
            <p className="text-sm text-muted">Description under the page title — 14/22 muted</p>
            <p className="text-xs font-medium text-subtle">Field label (Label) — 12/18 medium</p>
            <p className="text-xs text-subtle">Helper text — 12/18 regular</p>
            <p className="text-2xs text-muted">Date / small note — 10/14</p>
          </div>
        </Section>

        <Section id="radius" title="Radius & shadows">
          <Row label="radius">
            {["xs", "sm", "md", "lg", "pill"].map((r) => (
              <div key={r} className="flex flex-col items-center gap-1">
                <div className="size-16 border border-line bg-surface-subtle" style={{ borderRadius: `var(--radius-${r})` }} />
                <span className="text-2xs text-muted">{r}</span>
              </div>
            ))}
          </Row>
          <Row label="shadow">
            {["card", "soft", "overlay", "popper", "fab"].map((s) => (
              <div key={s} className="flex h-16 w-28 items-center justify-center rounded-lg bg-white text-xs text-muted" style={{ boxShadow: `var(--shadow-${s})` }}>
                {s}
              </div>
            ))}
          </Row>
        </Section>

        <Section id="icons" title={`Icons (${Object.keys(icons).length})`}>
          <div className="grid grid-cols-4 gap-2 sm:grid-cols-6 xl:grid-cols-10">
            {Object.entries(icons).map(([name, Icon]) => (
              <div key={name} className="flex flex-col items-center gap-1 rounded-md border border-line-subtle p-2 text-gray-700">
                <Icon size={20} />
                <span className="w-full truncate text-center text-2xs text-muted" dir="ltr">
                  {name}
                </span>
              </div>
            ))}
          </div>
        </Section>

        <Section id="buttons" title="Buttons">
          <Row label="variants">
            <Button>Primary</Button>
            <Button variant="outline">Primary outline</Button>
            <Button variant="secondary">Cancel</Button>
            <Button variant="danger">Delete</Button>
            <Button variant="danger-outline">Delete</Button>
            <Button variant="warning">Upgrade</Button>
            <Button variant="success">Success</Button>
            <Button variant="info">Info</Button>
            <Button variant="purple">Purple</Button>
            <Button variant="light">Light</Button>
            <Button variant="link" strong>
              Mark all as read
            </Button>
          </Row>
          <Row label="disabled">
            <Button disabled>Save</Button>
            <Button variant="outline" disabled>
              Open account
            </Button>
            <Button variant="secondary" disabled>
              Link your existing account
            </Button>
            <Button variant="danger" disabled>
              Delete
            </Button>
          </Row>
          <Row label="sizes / icon / loading">
            <Button size="sm">Small 36</Button>
            <Button>Default 38</Button>
            <Button size="md">Medium 40</Button>
            <Button size="lg">Large 44</Button>
            <Button>
              <PlusIcon /> New search
            </Button>
            <Button variant="secondary">
              <FilterIcon /> Filter
            </Button>
            <Button loading>Saving</Button>
            <Button variant="secondary" size="icon" aria-label="more">
              <MoreVerticalIcon />
            </Button>
            <Button variant="ghost" size="icon" aria-label="edit">
              <PenIcon />
            </Button>
            <Button variant="secondary" block className="max-w-80">
              <GoogleIcon /> Sign in with SSO
            </Button>
          </Row>
        </Section>

        <Section id="badges" title="Badges">
          {(["soft", "solid"] as const).map((a) => (
            <Row key={a} label={a}>
              {(["primary", "gray", "success", "danger", "info", "warning", "orange", "pink", "purple"] as const).map((c) => (
                <Badge key={c} color={c} appearance={a}>
                  {c}
                </Badge>
              ))}
            </Row>
          ))}
          <Row label="sizes / counter">
            <Badge color="info" size="sm">
              New
            </Badge>
            <Badge color="warning">Analytics</Badge>
            <Badge color="success" size="md">
              Verified
            </Badge>
            <Badge color="danger" size="lg">
              Cancelled
            </Badge>
            <CountBadge>2</CountBadge>
          </Row>
        </Section>

        <Section id="forms" title="Inputs">
          <FieldGrid>
            <Field label="Name">
              <Input placeholder="e.g. Ivan Petrov" defaultValue="OOO TechnoPanel" />
            </Field>
            <Field label="Website URL">
              <Input readOnly value="https://radar.example/s/RlQ2HSej" />
            </Field>
            <Field label="Name" error="Required field, please fill it in">
              <Input placeholder="e.g. Ivan Petrov" />
            </Field>
            <Field label="Phone number" optionalLabel="optional">
              <PhoneInput value={phone} onChange={setPhone} />
            </Field>
            <Field label="Project country">
              <Combobox
                value={country}
                onValueChange={setCountry}
                placeholder="e.g. Russia"
                searchPlaceholder="Search..."
                options={[
                  { value: "sa", label: "Russia" },
                  { value: "ae", label: "Belarus" },
                  { value: "my", label: "Armenia" },
                  { value: "id", label: "Kazakhstan" },
                ]}
              />
            </Field>
            <Field label="Time zone" hint="The time zone keeps dates consistent across searches, reports and exports">
              <SimpleSelect
                defaultValue="riyadh"
                options={[
                  { value: "riyadh", label: "Europe / Moscow" },
                  { value: "dubai", label: "Europe / Samara" },
                  { value: "kl", label: "Asia / Yekaterinburg" },
                ]}
              />
            </Field>
            <Field label="Delivery date" optionalLabel="optional">
              <DatePicker value={date} onChange={setDate} placeholder="Example: 2025/06/12" />
            </Field>
            <Field label="Email" optionalLabel="optional">
              <Input disabled placeholder="example@email.com" />
            </Field>
            <Field label="Search">
              <Input size="sm" prefix={<SearchIcon />} placeholder="Search by supplier name, INN, email" />
            </Field>
            <Field label="Header search">
              <Input size="md" prefix={<SearchIcon />} suffix={<Kbd>Ctrl + K</Kbd>} placeholder="Search..." />
            </Field>
            <Field label="Description" className="md:col-span-2">
              <Textarea placeholder="Write a short description" maxLength={300} showCount value={text} onChange={(e) => setText(e.target.value)} />
            </Field>
            <Field label="Verification code">
              <OtpInput length={4} value={otp} onChange={setOtp} />
            </Field>
          </FieldGrid>
        </Section>

        <Section id="selection" title="Selection controls">
          <Row label="checkbox">
            <Checkbox />
            <Checkbox checked={checked} onCheckedChange={setChecked} />
            <Checkbox checked="indeterminate" />
            <Checkbox size="sm" defaultChecked />
            <Checkbox disabled />
            <CheckboxLabel label="Remember for 30 days" defaultChecked />
          </Row>
          <div className="grid gap-3 md:grid-cols-3">
            <CheckboxCard label="Delivery" defaultChecked />
            <CheckboxCard label="Warranty" />
            <CheckboxCard label="Certificates" disabled />
          </div>
          <Row label="radio">
            <RadioGroup defaultValue="all">
              <RadioItem value="all" label="All" />
              <RadioItem value="paid" label="Verified" />
              <RadioItem value="unpaid" label="Unverified" />
              <RadioItem value="x" label="Disabled" disabled />
            </RadioGroup>
          </Row>
          <RadioCards defaultValue="person" className="max-w-md">
            <RadioCard value="person">Individual</RadioCard>
            <RadioCard value="company">Company</RadioCard>
            <RadioCard value="gov">Government body</RadioCard>
          </RadioCards>
          <Row label="switch">
            <Switch />
            <Switch defaultChecked />
            <Switch disabled />
            <Switch disabled defaultChecked />
            <SwitchLabel label="Enabled" defaultChecked />
          </Row>
        </Section>

        <Section id="tabs" title="Tabs & secondary navigation">
          <Tabs defaultValue="basic">
            <TabsList>
              <TabsTrigger value="basic">Basic data</TabsTrigger>
              <TabsTrigger value="address">Address</TabsTrigger>
              <TabsTrigger value="contact" invalid>
                Contact details
              </TabsTrigger>
            </TabsList>
            <TabsContent value="basic" className="text-sm text-subtle">
              Tab content
            </TabsContent>
          </Tabs>
          <Tabs defaultValue="mobile">
            <TabsList variant="pill" className="w-[280px]" fullWidth>
              <TabsTrigger value="mobile">Mobile version</TabsTrigger>
              <TabsTrigger value="full">Full version</TabsTrigger>
            </TabsList>
          </Tabs>
          <Card variant="default">
            <TabsHeader>
              <Tabs defaultValue="all">
                <TabsList>
                  <TabsTrigger value="all">All</TabsTrigger>
                  <TabsTrigger value="orders">Searches</TabsTrigger>
                </TabsList>
              </Tabs>
            </TabsHeader>
          </Card>
          <SideNav className="xl:max-w-[300px]">
            <SideNavSection title="Analyst details">
              <SideNavItem href="#" icon={<UserCircleIcon />} active>
                Account settings
              </SideNavItem>
              <SideNavItem href="#" icon={<KeyIcon />}>
                Security settings
              </SideNavItem>
            </SideNavSection>
            <SideNavSection title="Project details">
              <SideNavItem href="#" icon={<BuildingIcon />}>
                Project settings
              </SideNavItem>
              <SideNavItem href="#" icon={<UsersIcon />}>
                Users & permissions
              </SideNavItem>
            </SideNavSection>
          </SideNav>
        </Section>

        <Section id="accordion" title="Accordions">
          <Accordion type="single" collapsible defaultValue="b" variant="highlight">
            <AccordionItem value="a">
              <AccordionTrigger icon={<HomeIcon />}>Complete contact details</AccordionTrigger>
              <AccordionContent>Content</AccordionContent>
            </AccordionItem>
            <AccordionItem value="b">
              <AccordionTrigger icon={<BrowserSearchIcon />}>Workspace design (highlight)</AccordionTrigger>
              <AccordionContent>
                <h4 className="mb-1 text-lg font-medium text-heading">🚀 Ready for your first search?</h4>
                <p className="text-sm text-subtle">To get started, make sure you complete the following steps</p>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
          <Accordion type="multiple" defaultValue={["x"]}>
            <AccordionItem value="x">
              <AccordionTrigger icon={<ShieldInfoIcon />}>Legal data (default)</AccordionTrigger>
              <AccordionContent className="pt-0 text-sm text-subtle">Section content</AccordionContent>
            </AccordionItem>
          </Accordion>
        </Section>

        <Section id="cards" title="Cards">
          <div className="grid gap-5 md:grid-cols-3">
            <StatCard title="Contract value" value="0 ₽" trend="0%" trendLabel="vs. last month" />
            <StatCard title="Known suppliers" value="12,400" trend="12%" trendDirection="up" trendLabel="vs. last month" />
            <StatCard title="Total searches" value="0" unit="searches" trend="3%" trendDirection="down" trendLabel="vs. last month" />
          </div>
          <SettingCard icon={<LockIcon />} title="Password" description="Protect your account with a strong password" actions={<Button variant="outline">Reset password</Button>} />
          <SettingCard icon={<GoogleIcon />} title="Sign in with SSO" description="Lets you sign in quickly with your organization account, no password needed" actions={<Button>Enable</Button>} />
          <div className="grid gap-4 md:grid-cols-2">
            <OptionCard active>
              <div className="h-24 rounded-lg bg-primary-600" />
              <div className="flex items-center justify-between">
                <div>
                  <h5 className="text-sm font-medium text-heading">Minimal layout</h5>
                  <p className="text-xs text-subtle">Fast single sign-on experience</p>
                </div>
                <Button variant="secondary">Customize</Button>
              </div>
            </OptionCard>
            <OptionCard>
              <div className="h-24 rounded-lg bg-gray-100" />
              <div className="flex items-center justify-between">
                <div>
                  <h5 className="text-sm font-medium text-heading">Compact layout</h5>
                  <p className="text-xs text-subtle">Detailed layout</p>
                </div>
                <Button disabled>Enable</Button>
              </div>
            </OptionCard>
          </div>
          <Card variant="internal">
            <p className="text-sm text-heading">Internal card (internal)</p>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Account details</CardTitle>
            </CardHeader>
            <CardBody className="text-sm text-subtle">Card body</CardBody>
            <CardFooter>
              <Button variant="secondary">Cancel</Button>
              <Button>Save</Button>
            </CardFooter>
          </Card>
        </Section>

        <Section id="alerts" title="Alerts">
          <Alert tone="warning" title="External registry checks are not available offline" description="Live registry checks need a network connection; pre-indexed data is still available" actions={<Button variant="warning">Upgrade</Button>} />
          <Alert tone="info" title="Import suggested suppliers" description="We prepared a list of suggested suppliers" actions={<Button>Smart add</Button>} />
          <Alert tone="success" title="Enabled" description="Data source enabled successfully" />
          <Alert tone="danger" title="Connection failed" description="Could not reach the registry" />
          <Alert tone="default" title="Note" description="Neutral alert" />
          <Alert appearance="inline" tone="info" title="You can edit images, the icon or the project summary from the workspace settings page" />
        </Section>

        <Section id="empty" title="Empty state">
          <Card variant="outlined">
            <EmptyState title="No searches yet" description="Describe what you need to procure and the system will map the supplier market for you" actions={<Button><PlusIcon /> New search</Button>} />
          </Card>
          <Card variant="outlined">
            <EmptyState size="small" icon={<FaceFrownIcon />} title="Nothing matches your search" description="Try a different search term" />
          </Card>
        </Section>

        <Section id="table" title="Table">
          <TableCard>
            <TableToolbar>
              <Input size="sm" wrapperClassName="max-w-80" prefix={<SearchIcon />} placeholder="Search by supplier name, INN, email" />
              <div className="flex items-center gap-3">
                {selected.length ? <BulkActions label="Actions" count={selected.length} /> : null}
                <Button variant="secondary" size="md">
                  <FilterIcon /> Filter
                </Button>
              </div>
            </TableToolbar>
            <Table>
              <TableHeader>
                <tr>
                  <TableCheckboxCell header>
                    <Checkbox checked={selected.length === 3 ? true : selected.length ? "indeterminate" : false} onCheckedChange={(v) => setSelected(v ? ["1", "2", "3"] : [])} />
                  </TableCheckboxCell>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Phone number</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Registered on</TableHead>
                  <TableHead>Actions</TableHead>
                </tr>
              </TableHeader>
              <TableBody>
                {[
                  ["1", "Ivan Petrov", "--", "+96650 123 4569", "success", "Verified"],
                  ["2", "Olga Ivanova", "sara@mail.com", "+96655 222 1100", "warning", "Pending"],
                  ["3", "Anna Smirnova", "khaled@mail.com", "+96650 999 8877", "danger", "Cancelled"],
                ].map(([id, name, mail, phoneNo, tone, status]) => (
                  <TableRow key={id} data-state={selected.includes(id) ? "selected" : undefined}>
                    <TableCheckboxCell>
                      <Checkbox checked={selected.includes(id)} onCheckedChange={(v) => setSelected((s) => (v ? [...s, id] : s.filter((x) => x !== id)))} />
                    </TableCheckboxCell>
                    <TableCell label="Name">
                      <TableMainCell media={<Symbol />} title={name} />
                    </TableCell>
                    <TableCell label="Email">{mail}</TableCell>
                    <TableCell label="Phone number">
                      <span dir="ltr">{phoneNo}</span>
                    </TableCell>
                    <TableCell label="Status">
                      <Badge color={tone as "success"}>{status}</Badge>
                    </TableCell>
                    <TableCell label="Registered on">2026/07/06</TableCell>
                    <TableCell>
                      <TableActions>
                        <Tooltip content="Edit">
                          <Button variant="ghost" size="icon" aria-label="edit">
                            <PenIcon />
                          </Button>
                        </Tooltip>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" aria-label="more">
                              <MoreVerticalIcon />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent>
                            <DropdownMenuItem>
                              <EyeIcon /> View details
                            </DropdownMenuItem>
                            <DropdownMenuItem tone="danger">
                              <TrashIcon /> Delete supplier
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableActions>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <TableFooter>
              <Pagination page={page} pageCount={5} onPageChange={setPage} />
              <PageSize label="Rows per page:" value={pageSize} onValueChange={setPageSize} allLabel="All" />
            </TableFooter>
          </TableCard>
        </Section>

        <Section id="overlays" title="Overlays">
          <Row>
            <Dialog>
              <DialogTrigger asChild>
                <Button>Form dialog (Dialog)</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add new supplier</DialogTitle>
                </DialogHeader>
                <DialogBody>
                  <Field label="Full name">
                    <Input placeholder="e.g. Ivan Petrov" />
                  </Field>
                  <Field label="Phone number" optionalLabel="optional">
                    <PhoneInput value="" />
                  </Field>
                  <Field label="Region" optionalLabel="optional">
                    <SimpleSelect placeholder="e.g. Russian" options={[{ value: "sa", label: "Russian" }]} />
                  </Field>
                </DialogBody>
                <DialogFooter>
                  <DialogClose asChild>
                    <Button variant="secondary">Cancel</Button>
                  </DialogClose>
                  <Button>Add</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            <ConfirmDialog
              trigger={<Button variant="danger-outline">Confirm dialog</Button>}
              icon={<TrashIcon />}
              title="Delete this supplier?"
              description="After deleting, this supplier and its linked records cannot be restored"
              confirm={<Button variant="danger">Delete</Button>}
              cancel={
                <DialogClose asChild>
                  <Button variant="secondary">Cancel</Button>
                </DialogClose>
              }
            />
            <Drawer>
              <DrawerTrigger asChild>
                <Button variant="secondary">
                  <FilterIcon /> Filter drawer (Drawer)
                </Button>
              </DrawerTrigger>
              <DrawerContent>
                <DrawerHeader>
                  <DrawerTitle>Filter</DrawerTitle>
                </DrawerHeader>
                <DrawerBody>
                  <Accordion type="multiple" variant="flush" defaultValue={["op"]}>
                    <AccordionItem value="op">
                      <AccordionTrigger>Contract details</AccordionTrigger>
                      <AccordionContent>
                        <DrawerSection className="px-0">
                          <Field label="Contract number" hint="Enter multiple values separated by a comma (,) between values.">
                            <Input placeholder="Example: 011111111" />
                          </Field>
                          <Field label="Status">
                            <RadioGroup defaultValue="all">
                              <RadioItem value="all" label="All" />
                              <RadioItem value="paid" label="Verified" />
                              <RadioItem value="unpaid" label="Unverified" />
                            </RadioGroup>
                          </Field>
                          <Field label="Contract date">
                            <DatePicker placeholder="e.g. This week" />
                          </Field>
                        </DrawerSection>
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                </DrawerBody>
                <DrawerFooter>
                  <Button variant="secondary">Reset</Button>
                  <Button>Apply</Button>
                </DrawerFooter>
              </DrawerContent>
            </Drawer>
            <Tooltip content="Visibility">
              <Button variant="secondary">Tooltip</Button>
            </Tooltip>
          </Row>
          <ToastDemo />
        </Section>

        <Section id="upload" title="Upload & calendar">
          <Row>
            <ImageUpload label="click to upload" />
            <div className="w-full max-w-md">
              <FileDropzone title="Drag the file here or" action="click to upload" hint="PDF, PNG, JPG (Maximum: 2MB)" />
            </div>
          </Row>
          <div className="max-w-md">
            <FileItem name="passport-scan.pdf" meta="Uploaded successfully" status="success" icon={<FilePdfIcon />} onRemove={() => {}} />
          </div>
          <Card variant="outlined" className="w-fit p-3">
            <Calendar mode="single" selected={new Date()} disabled={{ before: new Date() }} />
          </Card>
        </Section>

        <Section id="loading" title="Loading">
          <Row>
            <Spinner />
            <Spinner size={24} className="text-primary-700" />
            <div className="flex w-64 flex-col gap-2">
              <Skeleton />
              <Skeleton className="w-2/3" />
              <Skeleton className="h-10 rounded-md" />
            </div>
          </Row>
        </Section>

        <Section id="sr-extensions" title="Supplier Radar extensions">
          <Row label="ScoreStat (known / unknown) · ScorePill">
            <div className="grid w-full max-w-md grid-cols-3 gap-4">
              <ScoreStat label="Match" value={87} />
              <ScoreStat label="Confidence" value={46} tone="danger" />
              <ScoreStat label="Confidence" value={null} unknownLabel="no data" />
            </div>
            <ScorePill label="Match" value={87} />
            <ScorePill label="Confidence" value={null} tone="gray" />
          </Row>
          <Row label="ContributionList (points sum to the total; N/A rows stay listed)">
            <ContributionList
              className="w-full max-w-md"
              naLabel="not applicable"
              rows={[
                { key: "semantic", label: "Semantic similarity", points: 29, applicable: true },
                { key: "attributes", label: "Characteristics", points: 16, applicable: true, highlight: true },
                { key: "experience", label: "Procurement experience", points: 8, applicable: true },
                { key: "supplier_type", label: "Supplier type", points: 0, applicable: false },
              ]}
              total={{ label: "Match", value: 53 }}
            />
          </Row>
          <Row label="CheckList (positive / risk / neutral)">
            <CheckList
              items={[
                { key: "a", label: "14 similar contracts" },
                { key: "b", label: "Manufacturer not verified", tone: "risk", description: "No registry or catalogue confirms it." },
                { key: "c", label: "Has already supplied AIS customers", tone: "neutral" },
              ]}
            />
          </Row>
          <Row label="EvidenceItem · ExternalLink">
            <EvidenceItem className="w-full max-w-lg" type="Manufacturer registry" typeColor="success" claim="Product is listed in the industrial products registry" sourceName="Registry (demo)" sourceUrl="https://example.com/demo/registry" observedLabel="observed 2026/09/12" confidenceLabel="reliability 100" />
            <ExternalLink href="https://example.com/demo">example.com/demo</ExternalLink>
          </Row>
          <Row label="CompareTable (sticky label column, highlighted row)">
            <CompareTable>
              <CompareHeadRow label="Request">
                <CompareHeadCell>Supplier A</CompareHeadCell>
                <CompareHeadCell>Supplier B</CompareHeadCell>
              </CompareHeadRow>
              <tbody>
                <CompareSection label="Scores" colSpan={3} />
                <CompareRow label="Match">
                  <CompareCell>95</CompareCell>
                  <CompareCell>84</CompareCell>
                </CompareRow>
                <CompareRow label="Region" highlight highlightLabel="Largest difference">
                  <CompareCell>+5</CompareCell>
                  <CompareCell>+0</CompareCell>
                </CompareRow>
              </tbody>
            </CompareTable>
          </Row>
          <Row label="ActionBar — floating tray (see /results); TopBar — top navigation shell (see /search)">
            <span className="text-sm text-muted">Rendered in the product screens.</span>
          </Row>
        </Section>
      </AppShell>
    </ToastProvider>
  );
}
