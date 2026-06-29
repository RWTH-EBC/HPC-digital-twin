import { useEffect, useState, useRef } from "react";

const useTemplateNameAutocomplete = <Template extends { templateName: string }>(
  data: Template[],
  inputRef: React.RefObject<HTMLInputElement | null> | null,
  options?: {
    onInputChange?: (value: string) => void;
    onConfirm?: (value: string) => void;
  }
) => {
  const [searchValue, setSearchValue] = useState("");
  const [suggestions, setSuggestions] = useState<Template[]>([]);
  const [activeSuggestion, setActiveSuggestion] = useState(0);
  const [isOpen, setIsOpen] = useState(false);

  // ref for highlighted menu item
  const activeItemRef = useRef<HTMLDivElement | null>(null);

  // attach ref to active suggestion
  const setActiveItemRef = (el: HTMLDivElement | null) => {
    activeItemRef.current = el;
  };

  // Confirm selection from suggestions
  const confirmSelection = (value: string) => {
    if (!value.trim()) return;

    setSearchValue(value);
    setSuggestions([]);
    setIsOpen(false);

    // setTemplateName
    options?.onInputChange?.(value);
    // setSelectedTemplate;
    options?.onConfirm?.(value);
  };

  // Auto-scroll to active suggestion
  useEffect(() => {
    if (activeItemRef.current) {
      activeItemRef.current.scrollIntoView({
        block: "nearest",
        behavior: "smooth",
      });
    }
  }, [activeSuggestion]);

  // Handle input changes
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchValue(value);

    options?.onInputChange?.(value);

    if (value === "") {
      setSuggestions(data); // show all suggestions
      setActiveSuggestion(0);
      return;
    }
    const filtered = data.filter((item) =>
      item.templateName.toLowerCase().startsWith(value.toLowerCase())
    );
    setSuggestions(filtered);
    setIsOpen(true);
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" && activeSuggestion < suggestions.length - 1) {
      setActiveSuggestion(activeSuggestion + 1);
    } else if (e.key === "ArrowUp" && activeSuggestion > 0) {
      setActiveSuggestion(activeSuggestion - 1);
    } else if (e.key === "Enter" && suggestions[activeSuggestion]) {
      confirmSelection(suggestions[activeSuggestion].templateName);
    } else if (e.key === "Escape") {
      setSuggestions([]);
    }
  };

  // Handle suggestion click
  const handleClick = (template: Template) => {
    confirmSelection(template.templateName);
  };

  // Handle input cursor focus
  const handleFocus = () => {
    if (searchValue === "") {
      setSuggestions(data);
      setActiveSuggestion(0);
    }
    setIsOpen(true);
  };

  return {
    searchValue,
    suggestions,
    activeSuggestion,
    isOpen,
    setIsOpen,
    setActiveSuggestion,
    setActiveItemRef,
    handleChange,
    handleKeyDown,
    handleClick,
    handleFocus,
  };
};

export default useTemplateNameAutocomplete;
