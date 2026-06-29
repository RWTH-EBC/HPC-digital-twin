"use client";

import PageTitle from "@/components/PageTitle";
import Image from "next/image";


export default function Home() {
  return (
		<div className="grid grid-rows-[20px_1fr_220px] items-center justify-items-center [calc(100vh-74px)] p-8 pb-20 gap-16 sm:p-20">
      <main className="flex flex-col gap-8 row-start-2 items-center sm:items-start">
				<PageTitle title="Willkommen beim IT-Zauber Dashboard" />
				<Image src="/images/logo.svg" alt="logo" width={300} height={100} />
			</main>
		</div>
  );
}
