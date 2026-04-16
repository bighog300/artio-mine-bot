import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Alert, Badge, Button, Checkbox, IconButton, Input, Radio, Select, Spinner, Switch, TextArea } from "@/components/ui";

describe("ui foundation components", () => {
  it("renders loading button state", () => {
    render(<Button loading>Saving</Button>);

    const button = screen.getByRole("button", { name: /saving/i });
    expect(button).toBeDisabled();
    expect(screen.getByRole("status", { name: /button loading/i })).toBeInTheDocument();
  });

  it("supports icon button accessibility", () => {
    render(
      <IconButton aria-label="Close panel">
        <span aria-hidden>×</span>
      </IconButton>,
    );

    expect(screen.getByRole("button", { name: /close panel/i })).toBeInTheDocument();
  });

  it("renders input, select, and textarea labels", () => {
    render(
      <>
        <Input label="Name" defaultValue="Ada" />
        <Select label="Type" options={[{ label: "Artist", value: "artist" }]} />
        <TextArea label="Notes" defaultValue="Curated" />
      </>,
    );

    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Type")).toBeInTheDocument();
    expect(screen.getByLabelText("Notes")).toBeInTheDocument();
  });

  it("toggles checkbox, radio, and switch callbacks", async () => {
    const user = userEvent.setup();
    const onCheckboxChange = vi.fn();
    const onRadioChange = vi.fn();
    const onSwitchChange = vi.fn();

    render(
      <>
        <Checkbox id="approved" label="Approved" onChange={onCheckboxChange} />
        <Radio id="featured" name="status" label="Featured" onChange={onRadioChange} />
        <Switch id="enabled" label="Enabled" onChange={onSwitchChange} />
      </>,
    );

    await user.click(screen.getByLabelText("Approved"));
    await user.click(screen.getByLabelText("Featured"));
    await user.click(screen.getByLabelText("Enabled"));

    expect(onCheckboxChange).toHaveBeenCalledWith(true);
    expect(onRadioChange).toHaveBeenCalledWith(true);
    expect(onSwitchChange).toHaveBeenCalledWith(true);
  });

  it("renders alert, badge, and spinner", () => {
    render(
      <>
        <Alert title="Saved" description="Record updated" variant="success" />
        <Badge variant="warning">Needs review</Badge>
        <Spinner label="Loading records" />
      </>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Saved");
    expect(screen.getByText("Needs review")).toBeInTheDocument();
    expect(screen.getByRole("status", { name: /loading records/i })).toBeInTheDocument();
  });
});
